import sys
import json
import sqlite3
import os
import re
import numpy as np
import pandas as pd
from datetime import datetime
from collections import OrderedDict
from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify
import joblib

app = Flask(__name__)
app.secret_key = 'url-analyzer-secret-key-2026'

print("=== ML URL ANALYZER STARTING ===", file=sys.stderr)
sys.stderr.flush()

# ========================================
# КЭШ
# ========================================
class LRUCache:
    def __init__(self, max_size=1000):
        self.data = OrderedDict()
        self.max_size = max_size

    def get(self, key):
        if key in self.data:
            self.data.move_to_end(key)
            return self.data[key]
        return None

    def put(self, key, val):
        self.data[key] = val
        if len(self.data) > self.max_size:
            self.data.popitem(last=False)

cache = LRUCache(max_size=1000)

# ========================================
# БАЗА ДАННЫХ
# ========================================
def get_conn():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/feedback.db")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            feedback TEXT NOT NULL,
            label INTEGER,
            timestamp TEXT NOT NULL
        )
    """)
    return conn

# ========================================
# ЗАГРУЗКА МОДЕЛИ
# ========================================
model = None
feature_columns = []

print("Loading model...", file=sys.stderr)

try:
    if os.path.exists("ml/models/rf_sprint2.pkl"):
        model = joblib.load("ml/models/rf_sprint2.pkl")
        print("✅ RandomForest model loaded", file=sys.stderr)
    elif os.path.exists("ml/model.pkl"):
        model = joblib.load("ml/model.pkl")
        print("✅ ML model loaded", file=sys.stderr)
    else:
        print("⚠️ No ML model found, using heuristics only", file=sys.stderr)
except Exception as e:
    print(f"⚠️ Error loading model: {e}", file=sys.stderr)

# ========================================
# ЭВРИСТИКИ
# ========================================
SUSPICIOUS_WORDS = {
    "path": ["login", "verify", "secure", "account", "profile", "payment", "bank", "update", "confirm"],
    "param": ["redirect", "url", "return", "next", "goto", "target", "redir", "u", "redirect_url"],
    "domain": ["bank", "paypal", "credit", "crypto", "wallet", "login", "account"],
}

def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.lower().rstrip("/")

def is_valid_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")) or " " in url:
        return False
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        return bool(netloc and "." in netloc.split(":")[0])
    except:
        return False

def is_localhost(url: str) -> bool:
    return bool(re.search(r"localhost|127\.0\.0\.1|192\.168|10\.", url, re.IGNORECASE))

def has_homoglyphs(url: str) -> bool:
    homoglyph_set = "аеосухрс"
    return any(c in homoglyph_set for c in url)

def has_brand_phishing(url: str) -> bool:
    brands = ["paypal", "google", "apple", "sberbank", "facebook"]
    url_lower = url.lower()
    return any(brand in url_lower and any(w in url_lower for w in ["login", "verify"]) for brand in brands)

def is_typosquatting(url: str) -> bool:
    popular = ["google", "yandex", "sberbank", "paypal"]
    try:
        netloc = urlparse(url).netloc.lower()
        return any(p in netloc and netloc != p for p in popular)
    except:
        return False

def is_shortener(url: str) -> bool:
    return any(s in url.lower() for s in ['bit.ly', 'goo.gl', 'tinyurl', 'cutt.ly', 't.ly'])

def has_suspicious_path(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(w in path for w in SUSPICIOUS_WORDS["path"])

def has_suspicious_params(url: str) -> bool:
    query = urlparse(url).query.lower()
    return any(w in query for w in SUSPICIOUS_WORDS["param"])

def is_suspicious_tld(url: str) -> bool:
    suspicious = [".xyz", ".top", ".club", ".tk", ".ml"]
    return any(tld in url.lower() for tld in suspicious)

def has_numbers_in_domain(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc
        return sum(c.isdigit() for c in netloc) > 5
    except:
        return False

def is_short_domain(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.split(".")[0]
        return 1 < len(netloc) <= 3
    except:
        return False

def is_ip_with_port(url: str) -> bool:
    return bool(re.search(r'\d+\.\d+\.\d+\.\d+:\d+', url))

def has_many_subdomains(url: str) -> bool:
    try:
        parts = urlparse(url).netloc.split(".")
        return len(parts) > 4
    except:
        return False

def compute_score(url: str) -> float:
    signals = []
    url_lower = url.lower()
    
    # Супер-фишинг
    if any(x in url_lower for x in ['g00gle', 'go0gle', 'goog1e']):
        return 0.95
    
    # Кириллица в домене
    if has_homoglyphs(url):
        signals.append(0.60)
    
    # Бренды с подозрительными словами
    if has_brand_phishing(url):
        signals.append(0.50)
    
    # Основные эвристики
    if not url.startswith('https://'): 
        signals.append(0.15)
    if is_shortener(url): 
        signals.append(0.35)
    if is_suspicious_tld(url): 
        signals.append(0.30)
    if is_ip_with_port(url): 
        signals.append(0.45)
    
    total = sum(signals)
    return min(total, 1.0)

def get_explanations(url):
    exps = []

    if 'g00gle' in url.lower() or 'go0gle' in url.lower():
        exps.append("🚨 ПОДДЕЛЬНЫЙ GOOGLE (g00gle → google)")
        return exps

    if not url.startswith('https'):
        exps.append("Отсутствует защищённое соединение HTTPS")
    if is_shortener(url):
        exps.append("Сервис сокращения ссылок")
    if has_brand_phishing(url):
        exps.append("Ссылка использует имя известного бренда для обмана")
    if is_typosquatting(url):
        exps.append("Ссылка имитирует домен известного сайта")
    if has_suspicious_path(url):
        exps.append("В пути ссылки обнаружены подозрительные слова")
    if has_suspicious_params(url):
        exps.append("Ссылка содержит подозрительные параметры перенаправления")
    if has_numbers_in_domain(url):
        exps.append("Домен содержит много цифр")
    if is_short_domain(url):
        exps.append("Слишком короткий домен")
    if is_suspicious_tld(url):
        exps.append("Подозрительная доменная зона")
    if is_ip_with_port(url):
        exps.append("IP-адрес с портом")
    if has_many_subdomains(url):
        exps.append("Слишком много поддоменов")

    if not exps:
        exps.append("Явных признаков фишинга не обнаружено")

    return exps

# ========================================
# ROUTES
# ========================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/check", methods=["POST"])
def check_url():
    data = request.json
    raw_url = data.get("url", "").strip()
    
    if not raw_url:
        return jsonify({"error": "URL is required"}), 400
    
    url = normalize_url(raw_url)
    
    if not is_valid_url(url):
        return jsonify({"error": "Invalid URL format"}), 400
    
    if is_localhost(url):
        return jsonify({
            "url": raw_url,
            "verdict": "safe",
            "score": 0,
            "verdict_text": "⚠️ Локальный адрес",
            "explanations": ["Локальный адрес пропущен"]
        })
    
    # Проверяем кэш
    cached = cache.get(url)
    if cached:
        return jsonify(cached)
    
    # Вычисляем результат
    score = compute_score(url)
    
    if score > 0.7:
        verdict = "dangerous"
        verdict_text = "🔴 ОПАСНО! Фишинговая ссылка"
    elif score > 0.4:
        verdict = "suspicious"
        verdict_text = "🟡 ПОДОЗРИТЕЛЬНО"
    else:
        verdict = "safe"
        verdict_text = "🟢 БЕЗОПАСНО"
    
    result = {
        "url": raw_url,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "score": round(score * 100),
        "explanations": get_explanations(url)
    }
    
    # Сохраняем в кэш
    cache.put(url, result)
    
    return jsonify(result)

@app.route('/feedback', methods=['POST'])
def save_feedback():
    try:
        data = request.json
        url = data.get('url')
        
        # Поддерживаем оба формата
        if 'label' in data:
            label = int(data.get('label'))
            feedback = f"label_{label}"
        else:
            user_verdict = data.get('user_verdict')
            model_verdict = data.get('model_verdict')
            comment = data.get('comment', '')
            
            # Преобразуем user_verdict в label
            label_map = {'dangerous': 1, 'suspicious': 1, 'safe': 0, 'other': None}
            label = label_map.get(user_verdict)
            feedback = f"model:{model_verdict}|user:{user_verdict}|comment:{comment}"
        
        conn = get_conn()
        conn.execute(
            "INSERT INTO feedbacks (url, feedback, label, timestamp) VALUES (?, ?, ?, ?)",
            (url, feedback, label, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        
        return jsonify({'status': '✅ Feedback saved!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/feedbacks_count', methods=['GET'])
def feedbacks_count():
    try:
        conn = get_conn()
        count = conn.execute("SELECT COUNT(*) FROM feedbacks WHERE label IN (0,1)").fetchone()[0]
        conn.close()
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'count': 0})

@app.route('/admin/retrain', methods=['POST'])
def retrain_model():
    global model
    try:
        conn = get_conn()
        df = pd.read_sql("SELECT url, label FROM feedbacks WHERE label IN (0,1)", conn)
        conn.close()
        
        if len(df) < 5:
            return jsonify({'status': f'❌ Need at least 5 samples, have {len(df)}'})
        
        # Здесь нужно добавить реальное извлечение признаков
        # Пока используем простую эвристику
        features = []
        for url in df['url']:
            score = compute_score(url)
            features.append([score])
        
        X_new = np.array(features)
        y_new = df['label'].values
        
        if model is not None:
            model.fit(X_new, y_new)
            os.makedirs("ml/models", exist_ok=True)
            joblib.dump(model, "ml/models/rf_sprint2.pkl")
            return jsonify({'status': f'✅ Model retrained on {len(df)} samples!'})
        else:
            # Создаем простую модель если её нет
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(n_estimators=50, random_state=42)
            model.fit(X_new, y_new)
            os.makedirs("ml/models", exist_ok=True)
            joblib.dump(model, "ml/models/rf_sprint2.pkl")
            return jsonify({'status': f'✅ New model created and trained on {len(df)} samples!'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/feedbacks')
def admin_feedbacks():
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT id, url, feedback, label, timestamp FROM feedbacks ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
        conn.close()
        
        html = "<h1>📊 Отзывы для ML (" + str(len(rows)) + ")</h1>"
        html += "<style>table{border-collapse:collapse;width:100%;}th,td{border:1px solid silver;padding:8px;text-align:left;}</style>"
        html += "<table><th>ID</th><th>URL</th><th>Label</th><th>Feedback</th><th>Дата</th></tr>"
        
        for row in rows:
            id_, url, feedback, label, timestamp = row
            url_short = (url[:60] + "...") if len(url) > 60 else url
            label_text = "🔴 PHISHING" if label == 1 else "🟢 SAFE" if label == 0 else "❓"
            html += f"""
            <tr>
                <td>{id_}</td>
                <td><a href="{url}" target="_blank">{url_short}</a></td>
                <td>{label_text}</td>
                <td>{feedback[:50]}</td>
                <td>{timestamp}</td>
            </tr>
            """
        
        html += "</table><br><a href='/'>← На главную</a>"
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        return f"<h1>Ошибка</h1><p>{e}</p><a href='/'>На главную</a>", 500

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": model is not None,
        "cache_size": len(cache.data)
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
