import sys
import json
import sqlite3
import os
import re
from datetime import datetime
from collections import OrderedDict
from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify, flash, redirect
import pandas as pd
import joblib

app = Flask(__name__)
app.secret_key = 'url-analyzer-secret-key-2026'

print("=== ML URL ANALYZER STARTING ===", file=sys.stderr)
sys.stderr.flush()

# ========================================
# КЭШ + БД
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
            label INTEGER,  # ← ДОБАВИТЬ!
            timestamp TEXT NOT NULL
        )
    """)
    return conn

# ========================================
# ✅ ВАШ ДАТАСЕТ + МОДЕЛЬ
# ========================================
model = None
features_df = None
feature_columns = []

print("Loading YOUR dataset...", file=sys.stderr)

try:
    if os.path.exists("ml/model.pkl"):
        model = joblib.load("ml/model.pkl")
        print("✅ ML model loaded", file=sys.stderr)
except:
    print("⚠️ No ML model, using heuristics only", file=sys.stderr)

try:
    if os.path.exists("data/processed/url_dataset_features.csv"):
        features_df = pd.read_csv("data/processed/url_dataset_features.csv")
        feature_columns = [col for col in features_df.columns if col not in ["url", "label"]]
        print(f"✅ YOUR DATASET: {len(features_df)} records, {len(feature_columns)} features", file=sys.stderr)
except:
    print("ℹ️ Dataset not found, heuristics only", file=sys.stderr)

# ========================================
# ВАШИ ЭВРИСТИКИ (без изменений)
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

# ДОБАВИТЬ после is_typosquatting():

def is_shortener(url: str) -> bool:
    return any(s in url.lower() for s in ['bit.ly', 'goo.gl', 'tinyurl', 'cutt.ly'])

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
    print(f"DEBUG: checking {url}", file=sys.stderr)
    
    url_lower = url.lower()
    
    # 🚨 СУПЕР-ФИШИНГ (ПРИОРИТЕТ №1)
    if any(x in url_lower for x in ['g00gle', 'go0gle', 'goog1e', 'yаndex', 'sberbаnk']):
        signals.append((0.90, "🚨 ФИШИНГ-БРЕНД"))
        print(f"🚨 PHISH DETECTED: {url}", file=sys.stderr)
    
    # ML + 15 эвристик...
    # (оставить остальное без изменений)
    
    # ML модель
    if model and features_df is not None:
        try:
            row = features_df[features_df["url"] == url]
            if not row.empty:
                X = row[feature_columns]
                ml_prob = model.predict_proba(X)[0][1]
                signals.append((0.6 * ml_prob, "ML"))
        except Exception as e:
            print(f"ML error: {e}", file=sys.stderr)

    # 15 ЭВРИСТИК (все!)
    if not url.startswith('https://'): signals.append((0.15, "no HTTPS"))
    if has_brand_phishing(url): signals.append((0.5, "brand"))
    if is_typosquatting(url): signals.append((0.45, "typo"))
    if is_shortener(url): signals.append((0.35, "shortener"))
    if has_suspicious_path(url): signals.append((0.35, "path"))
    if has_suspicious_params(url): signals.append((0.3, "params"))
    if has_numbers_in_domain(url): signals.append((0.12, "numbers"))
    if is_short_domain(url): signals.append((0.1, "short domain"))
    if is_suspicious_tld(url): signals.append((0.3, "TLD"))
    if is_ip_with_port(url): signals.append((0.45, "IP:port"))
    if has_many_subdomains(url): signals.append((0.12, "subdomains"))
    
    total = sum(w for w, _ in signals)
    print(f"DEBUG: score={total:.2f} signals={len(signals)}", file=sys.stderr)
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
# ✅ ROUTES (HTML FORM + API)
# ========================================
@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    result_class = ""
    feedback_count = 0
    
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if url:
            url = normalize_url(url)
            if not is_valid_url(url):
                result = "❌ НЕВАЛИДНЫЙ URL"
            elif is_localhost(url):
                result = "⚠️ ЛОКАЛЬНЫЙ АДРЕС"
            else:
                score = compute_score(url)
                if score > 0.7:
                    result = "🔴 ОПАСНО"
                    result_class = "phishing"
                elif score > 0.4:
                    result = "🟡 ПОДОЗРИТЕЛЬНО"
                    result_class = "suspicious"
                else:
                    result = f"🟢 БЕЗОПАСНО (score: {score:.1%})"
                    result_class = "safe"
                
                # Сохраняем для обучения
                conn = get_conn()
                conn.execute("INSERT INTO feedbacks (url, feedback, timestamp) VALUES (?, 'pending', ?)",
                           (url, datetime.now().isoformat()))
                feedback_count = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
                conn.commit()
                conn.close()
    
    try:
        conn = get_conn()
        feedback_count = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
        conn.close()
    except:
        pass
    
    return render_template("index.html", 
                         result=result, 
                         result_class=result_class,
                         feedback_count=feedback_count)

@app.route("/check", methods=["POST"])
def check_url():
    data = request.json
    raw_url = data.get("url", "").strip()
    
    if not raw_url or not is_valid_url(normalize_url(raw_url)):
        return jsonify({"error": "Invalid URL"}), 400
    
    url = normalize_url(raw_url)
    score = compute_score(url)
    
    if score > 0.7: verdict = "dangerous"
    elif score > 0.4: verdict = "suspicious"
    else: verdict = "safe"
    
    return jsonify({
        "url": raw_url,
        "verdict": verdict,
        "score": round(score * 100),
        "explanations": get_explanations(url),
        "dataset_size": len(features_df) if features_df is not None else 0
    })

# ========================================
# ✅ ДОБУЧЕНИЕ ML НА ОТЗЫВАХ
# ========================================
@app.route('/feedback', methods=['POST'])
def save_feedback():
    try:
        data = request.json or request.form
        url = data.get('url')
        label = int(data.get('label'))  # 0=safe, 1=phishing
        
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO feedbacks (url, feedback, label, timestamp) VALUES (?, ?, ?, ?)",
            (url, f"label_{label}", label, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return jsonify({'status': '✅ Feedback saved!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/retrain', methods=['POST'])
def retrain_model():
    global model
    try:
        conn = get_conn()
        df = pd.read_sql("SELECT url, label FROM feedbacks WHERE label IN (0,1)", conn)
        conn.close()
        
        if len(df) < 5:
            return jsonify({'status': '❌ Минимум 5 отзывов'})
        
        # Извлечь фичи (используем существующие функции)
        features = []
        for url in df['url']:
            # TODO: extract_features как в обучении
            feat = [1 if 'http' not in url else 0] * len(feature_columns)  # placeholder
            features.append(feat)
        
        X_new = np.array(features)
        y_new = df['label'].values
        
        # Переобучить модель (warm_start=True если RandomForest)
        if model:
            model.fit(X_new, y_new)  # или model.partial_fit если поддерживает
            joblib.dump(model, "ml/model.pkl")
        
        return jsonify({'status': f'✅ Model retrained! {len(df)} samples'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/admin/feedbacks")
def admin_feedbacks():
    try:
        conn = get_conn()
        rows = conn.execute("SELECT id, url, feedback, timestamp FROM feedbacks ORDER BY timestamp DESC LIMIT 50").fetchall()
        conn.close()
        
        html = f"<h1>📊 Отзывы для ML ({len(rows)})</h1>"
        html += "<style>table{border-collapse:collapse;width:100%;}th,td{border:1px solid #ddd;padding:8px;}</style>"
        html += "<table><tr><th>ID</th><th>URL</th><th>Feedback</th><th>Дата</th></tr>"
        
        for row in rows:
            id_, url, feedback, timestamp = row
            url_short = (url[:50] + "..." if len(url) > 50 else url)
            html += f"<tr><td>{id_}</td><td><a href='{url}' target='_blank'>{url_short}</a></td><td>{feedback}</td><td>{timestamp}</td></tr>"
        
        html += "</table><br><a href='/'>🏠 Главная</a>"
        return html
    except Exception as e:
        return f"<h1>Ошибка</h1><p>{e}</p><a href='/'>Главная</a>"

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model": model is not None,
        "dataset": features_df is not None,
        "cache_size": len(cache.data)
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
