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
app.secret_key = 'url-analyzer-secret-key-2026'  # ✅ Обязательно для flash!

print("=== SERVER STARTING ===", file=sys.stderr)
sys.stderr.flush()

class LRUCache:
    def __init__(self, max_size=1000):
        self.data = OrderedDict()
        self.max_size = max_size
        self.order = []

    def get(self, key):
        if key in self.data:
            self.order.remove(key)
            self.order.append(key)
            return self.data[key]
        return None

    def put(self, key, val):
        if key in self.data:
            self.order.remove(key)
        self.data[key] = val
        self.order.append(key)
        if len(self.data) > self.max_size:
            old = self.order.pop(0)
            del self.data[old]

cache = LRUCache(max_size=1000)


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    url = url.lower()
    return url.rstrip("/")

def is_valid_url(url: str) -> bool:
    url = url.lower()
    if not url.startswith(("http://", "https://")):
        return False
    if " " in url:
        return False

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if not netloc:
            return False
        if "[" in netloc or "]" in netloc:
            return False
        if "@" in netloc:
            return False
        return "." in netloc or ":" in netloc.split(":")[0]
    except Exception:
        return False

def is_localhost(url: str) -> bool:
    pattern = re.compile(
        r"localhost|127\\.0\\.0\\.1|192\\.168\\.\\d{1,3}\\.\\d{1,3}|"
        r"10\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
        re.IGNORECASE
    )
    return bool(pattern.search(url))


SUSPICIOUS_WORDS = {
    "path": ["login", "verify", "secure", "account", "profile", "payment", "bank", "update", "confirm"],
    "param": ["redirect", "url", "return", "next", "goto", "target", "redir", "u", "redirect_url"],
    "domain": ["bank", "paypal", "credit", "crypto", "wallet", "login", "account"],
    "encodings": ["%20", "%26", "%3F", "%3D", "%40"],
}

def has_homoglyphs(url: str) -> bool:
    homoglyph_set = "аеосухрс"
    return any(c in homoglyph_set for c in url.lower())

def has_encoding(url: str) -> bool:
    return bool(re.search(r"%[0-9A-Fa-f]{2}", url, re.IGNORECASE))

def has_suspicious_path(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(w in path for w in SUSPICIOUS_WORDS["path"])

def has_suspicious_params(url: str) -> bool:
    query = urlparse(url).query.lower()
    return any(w in query for w in SUSPICIOUS_WORDS["param"])

def is_short_domain(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.split(":")[0]
        if "." not in netloc:
            return False
        main = netloc.split(".")[0].lower()
        legitimate_short = ["ya", "vk", "ok", "fb", "gg", "go", "im", "tv", "io", "ru", "com"]
        return main not in legitimate_short and len(main) <= 3
    except Exception:
        return False

def has_numbers_in_domain(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.split(":")[0]
        return sum(c.isdigit() for c in netloc) > 5
    except Exception:
        return False

def has_many_subdomains(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.split(":")[0]
        parts = netloc.split(".")
        subdomains = parts[:-2]
        return len(subdomains) > 3
    except Exception:
        return False

def is_typosquatting(url: str) -> bool:
    """Проверяет, имитирует ли URL известный сайт"""
    popular_domains = [
        "google", "facebook", "youtube", "vk", "mail", "yandex",
        "gmail", "yahoo", "instagram", "twitter", "whatsapp",
        "telegram", "github", "sberbank", "sber", "paypal", "wellsfargo"
    ]
    try:
        netloc = urlparse(url).netloc.lower().split(":")[0]
        for popular in popular_domains:
            if popular in netloc and netloc != popular:
                if len(netloc) > len(popular):
                    return True
                suspicious = netloc.replace('0', 'o').replace('1', 'l').replace('5', 's')
                if popular in suspicious and suspicious != popular:
                    return True
    except Exception:
        pass
    return False

def is_suspicious_tld(url: str) -> bool:
    suspicious_tlds = [
        ".xyz", ".top", ".club", ".online", ".site", ".pw",
        ".cc", ".tk", ".ml", ".ga", ".cf", ".bid", ".win"
    ]
    return any(tld.lower() in url.lower() for tld in suspicious_tlds)

def is_too_long(url: str) -> bool:
    return len(url) > 200

def has_brand_phishing(url: str) -> bool:
    """Проверяет использование известных брендов в фишинговом контексте"""
    brands = [
        "paypal", "wellsfargo", "google", "apple", "microsoft", "amazon",
        "facebook", "instagram", "bank", "sberbank", "vtb", "tinkoff", "alfabank", "sber"
    ]
    url_lower = url.lower()
    
    for brand in brands:
        if brand in url_lower:
            legitimate = ["sberbank.ru", "sberbank.com", "paypal.com", "google.com", "apple.com"]
            if any(legit in url_lower for legit in legitimate):
                continue
            
            if brand in url_lower and any(word in url_lower for word in ["login", "verify", "secure", "account"]):
                return True
            
            try:
                netloc = urlparse(url).netloc.lower()
                if netloc.startswith(brand):
                    return True
            except:
                pass
            
            return True
    return False

def is_ip_with_port(url: str) -> bool:
    try:
        pattern = r"https?://(?:\\d{1,3}\\.){3}\\d{1,3}:\\d+"
        return bool(re.search(pattern, url, re.IGNORECASE))
    except Exception:
        return False

def has_suspicious_domain_pattern(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.lower().split(":")[0]
        if not netloc:
            return False
        return (
            netloc.count("-") > 3 or
            netloc.count(".") > 4 or
            bool(re.search(r"[bcdfghjklmnpqrstvwxyz]{6,}", netloc, re.IGNORECASE))
        )
    except Exception:
        return False

def has_suspicious_domain_words(url: str) -> bool:
    """Проверяет наличие подозрительных слов в домене"""
    suspicious_words = ['update', 'check', 'secure', 'verify', 'login', 'account', 'windows', 'support']
    try:
        domain = urlparse(url).netloc.lower().split(':')[0]
        return any(word in domain for word in suspicious_words)
    except:
        return False


print("Loading features and model...", file=sys.stderr)
sys.stderr.flush()

model = None
features_df = None
feature_columns = []

try:
    if os.path.exists("ml/model.pkl"):
        model = joblib.load("ml/model.pkl")
        print("✅ Модель загружена", file=sys.stderr)
    else:
        print("⚠️ ml/model.pkl не найден", file=sys.stderr)
except Exception as e:
    print(f"⚠️ Ошибка загрузки модели: {e}", file=sys.stderr)
    model = None

try:
    if os.path.exists("data/processed/url_dataset_features.csv"):
        features_df = pd.read_csv("data/processed/url_dataset_features.csv")
        feature_columns = [col for col in features_df.columns if col not in ["url", "label"]]
        print(f"✅ Датасет: {len(features_df)} записей, {len(feature_columns)} фич", file=sys.stderr)
    else:
        print("ℹ️ Датасет не найден, использую только эвристики", file=sys.stderr)
except Exception as e:
    print(f"⚠️ Ошибка загрузки датасета: {e}", file=sys.stderr)

print("🚀 Сервер готов к работе!", file=sys.stderr)
sys.stderr.flush()


def compute_score(url: str) -> float:
    signals = []

    if model and features_df is not None:
        try:
            row = features_df[features_df["url"] == url]
            if not row.empty:
                X = row[feature_columns]
                ml_prob = model.predict_proba(X)[0][1]
                signals.append((0.6, f"ML‑score: {ml_prob:.2f}"))
        except Exception:
            pass

    if has_brand_phishing(url):
        signals.append((0.4, "phishing известного бренда"))
    
    if any(shortener in url.lower() for shortener in ['bit.ly', 'goo.gl', 'tinyurl', 'cutt.ly']):
        signals.append((0.35, "сервис сокращения ссылок"))
    
    if any(shortener in url.lower() for shortener in ['bit.ly', 'tinyurl']) and not url.startswith('https'):
        signals.append((0.15, "сокращатель ссылок без HTTPS"))
    
    if is_typosquatting(url):
        signals.append((0.35, "подозрение на typosquatting"))
    
    if has_suspicious_path(url):
        signals.append((0.2, "подозрительный путь"))
    
    if has_suspicious_params(url):
        signals.append((0.25, "подозрительные параметры редиректа"))
    
    if has_numbers_in_domain(url):
        signals.append((0.12, "много цифр в домене"))
    
    if is_short_domain(url):
        signals.append((0.1, "слишком короткий домен"))
    
    if is_suspicious_tld(url):
        signals.append((0.25, "подозрительный TLD"))
    
    if is_ip_with_port(url):
        signals.append((0.3, "IP‑адрес с портом"))
    
    if has_suspicious_domain_pattern(url):
        signals.append((0.12, "подозрительная структура домена"))
    
    if has_suspicious_domain_words(url):
        signals.append((0.2, "подозрительное слово в домене"))

    if not signals:
        signals.append((0.05, "ничего явно подозрительного"))

    total = sum(w for w, _ in signals)
    return min(total, 1.0)

def get_explanations(url: str) -> list[str]:
    exps = []

    if not url.startswith("https://"):
        exps.append("Отсутствует защищённое соединение HTTPS")

    if has_suspicious_path(url):
        exps.append("В пути ссылки обнаружены подозрительные слова (login, verify и др.)")

    if has_suspicious_params(url):
        exps.append("Параметры URL могут использоваться для перенаправления на фишинг‑страницы")

    if has_brand_phishing(url):
        exps.append("Ссылка использует имя известного бренда для обмана")

    if has_numbers_in_domain(url):
        exps.append("Домен содержит много цифр (типично для фишинг‑сайтов)")

    if is_short_domain(url):
        exps.append("Слишком короткий домен (часто используется в фишинге)")

    if is_suspicious_tld(url):
        exps.append("Использована подозрительная доменная зона (эвристические TLD)")

    if is_ip_with_port(url):
        exps.append("Ссылка ведёт на IP‑адрес с портом (часто используется в фишинге)")

    if has_suspicious_domain_pattern(url):
        exps.append("Домен имеет подозрительную структуру (много дефисов/случайные символы)")

    if has_homoglyphs(url):
        exps.append("Ссылка содержит символы, похожие на латиницу (омоглифы)")

    if has_encoding(url):
        exps.append("Ссылка содержит закодированные символы (%XX)")

    if "bit.ly" in url.lower() or "goo.gl" in url.lower() or "tinyurl" in url.lower():
        exps.append("Использован сервис сокращения ссылок")

    if re.search(r"https?://(?:\\d{1,3}\\.){3}\\d{1,3}", url):
        exps.append("Ссылка содержит IP‑адрес вместо доменного имени")

    if "@" in url:
        exps.append("Ссылка содержит символ @ (может использоваться для обмана)")

    if not exps:
        exps.append("Явных признаков фишинга не обнаружено")

    return exps


def get_conn():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/feedback.db")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": model is not None,
        "features_df_loaded": features_df is not None
    })

@app.route("/check", methods=["POST"])
def check_url():
    data = request.json
    raw_url = data.get("url", "").strip()

    if not raw_url:
        return jsonify({"error": "URL не указан"}), 400

    url = normalize_url(raw_url)

    if not is_valid_url(url):
        return jsonify({
            "url": raw_url,
            "verdict": "invalid",
            "verdict_text": "❌ НЕВАЛИДНЫЙ URL",
            "score": 0,
            "explanations": [
                "URL должен начинаться с http:// или https://",
                "URL не должен содержать пробелов",
                "Пример: https://google.com"
            ]
        }), 400

    if is_localhost(url):
        return jsonify({
            "url": url,
            "verdict": "warning",
            "verdict_text": "⚠️ ЛОКАЛЬНЫЙ АДРЕС",
            "score": 0,
            "explanations": [
                "Локальные адреса (localhost, 192.168.x.x) не проверяются"
            ]
        })

    cached = cache.get(url)
    if cached:
        return jsonify(cached)

    score = compute_score(url)

    if score > 0.7:
        verdict = "dangerous"
        verdict_text = "🔴 ОПАСНО"
    elif score > 0.4:
        verdict = "suspicious"
        verdict_text = "🟡 ПОДОЗРИТЕЛЬНО"
    else:
        verdict = "safe"
        verdict_text = "🟢 БЕЗОПАСНО"

    explanations = get_explanations(url)

    result = {
        "url": raw_url,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "score": round(score * 100),
        "explanations": explanations
    }

    cache.put(url, result)
    return jsonify(result)

@app.route('/feedback', methods=['POST'])
def feedback():
    # ✅ Берём из JavaScript или формы
    url = request.form.get('url') or request.json.get('url') or ''
    feedback_type = request.form.get('feedback') or request.json.get('feedback') or 'unknown'
    
    print(f"🔥 FEEDBACK: url='{url}' type='{feedback_type}'")
    
    # ✅ Создаём таблицу ПРИНУДИТЕЛЬНО
    try:
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect("data/feedback.db")
        conn.execute('''CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT, feedback TEXT, timestamp TEXT
        );''')
        conn.commit()
        
        if url:  # Только если URL есть
            conn.execute("INSERT INTO feedbacks (url, feedback, timestamp) VALUES (?, ?, ?);",
                        (url, feedback_type, datetime.now().isoformat()))
            conn.commit()
            print("✅ FEEDBACK SAVED!")
        
        conn.close()
    except Exception as e:
        print(f"❌ DB ERROR: {e}")
    
    flash('✅ Отзыв отправлен!')
    return redirect('/')

@app.route("/admin/feedbacks")
def admin_feedbacks():
    try:
        conn = sqlite3.connect("data/feedback.db")
        rows = conn.execute(
            "SELECT id, url, feedback, timestamp FROM feedbacks ORDER BY timestamp DESC LIMIT 50;"
        ).fetchall()
        conn.close()

        if not rows:
            return "<h1>📋 Отзывы</h1><p>📭 Пока нет отзывов</p><a href='/'>Главная</a>"

        html = f"<h1>📋 Отзывы ({len(rows)})</h1><table border='1' style='border-collapse: collapse;'><tr><th>ID</th><th>URL</th><th>Отзыв</th><th>Дата</th></tr>"
        for row in rows:
            id_, url, feedback, timestamp =
            url_short = (url[:50] + "...") if len(url) > 50 else url
            html += f"<tr><td>{id_}</td><td><a href='{url}' target='_blank'>{url_short}</a></td><td>{feedback}</td><td>{timestamp}</td></tr>"
        html += "</table><br><a href='/'>Главная</a>"
        return html

    except Exception as e:
        return f"<h1>Ошибка</h1><p>{str(e)}</p><a href='/'>Главная</a>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
