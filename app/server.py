from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from config import Config
import logging
logger = logging.getLogger(__name__)
from security import security
from src.ensemble_predictor import ensemble
from src.feedback_system import FeedbackSystem
from urllib.parse import urlparse

app = Flask(__name__, 
            template_folder=str(Config.TEMPLATES_DIR),
            static_folder=str(Config.STATIC_DIR))

# Инициализация
Config.init_dirs()
feedback_system = FeedbackSystem()

# Кэш
cache = {}

def get_cached(url):
    if url in cache:
        data, timestamp = cache[url]
        if datetime.now() - timestamp < timedelta(hours=Config.CACHE_TTL_HOURS):
            return data
        del cache[url]
    return None

def set_cached(url, data):
    if len(cache) > Config.CACHE_MAX_SIZE:
        oldest = min(cache.keys(), key=lambda k: cache[k][1])
        del cache[oldest]
    cache[url] = (data, datetime.now())

def normalize_url(url):
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.lower().rstrip('/')

def get_explanations(url, score):
    explanations = []
    
    if not url.startswith('https://'):
        explanations.append("❌ Отсутствует защищённое соединение HTTPS")
    
    if any(shortener in url for shortener in Config.URL_SHORTENERS):
        explanations.append("🔗 Используется сервис сокращения ссылок")
    
    if any(brand in url.lower() for brand in Config.POPULAR_BRANDS):
        if not any(legit in url.lower() for legit in Config.LEGITIMATE_DOMAINS):
            explanations.append("⚠️ Ссылка использует имя известного бренда для обмана")
    
    if any(tld in url for tld in Config.SUSPICIOUS_TLDS):
        explanations.append("🌐 Подозрительная доменная зона")
    
    if score > 0.7:
        explanations.append("🔴 Высокая вероятность фишинга")
    elif score > 0.4:
        explanations.append("🟡 Обнаружены подозрительные признаки")
    
    if not explanations:
        explanations.append("✅ Явных признаков фишинга не обнаружено")
    
    return explanations

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'models': {
            'random_forest': ensemble.random_forest is not None,
            'xgboost': ensemble.xgboost is not None
        },
        'cache_size': len(cache)
    })

@app.route('/check', methods=['POST'])
#@security.rate_limit()
def check_url():
    data = request.json
    raw_url = data.get('url', '').strip()
    
    if not raw_url:
        return jsonify({'error': 'URL не указан'}), 400
    
    is_valid, error_msg = security.validate_url(raw_url)
    if not is_valid:
        return jsonify({
            'url': raw_url,
            'verdict': 'invalid',
            'verdict_text': '❌ НЕВАЛИДНЫЙ URL',
            'score': 0,
            'explanations': [error_msg]
        }), 400
    
    url = normalize_url(raw_url)
    cached = get_cached(url)
    if cached:
        return jsonify(cached)
    
    if ensemble.is_model_loaded():
        predictions = ensemble.predict_proba(url)
        score = predictions['ensemble']
        logger.info(f"ML: {url[:50]}... Score={score:.3f}")
    else:
        logger.warning("Модели не загружены, эвристики")
        score = 0.3
    
    if score > Config.DANGEROUS_THRESHOLD:
        verdict, text = "dangerous", "🔴 ОПАСНО"
    elif score > Config.SUSPICIOUS_THRESHOLD:
        verdict, text = "suspicious", "🟡 ПОДОЗРИТЕЛЬНО"
    else:
        verdict, text = "safe", "🟢 БЕЗОПАСНО"
    
    result = {
        'url': raw_url,
        'verdict': verdict,
        'verdict_text': text,
        'score': round(score * 100),
        'explanations': get_explanations(url, score),
        'model_details': {
            'random_forest': round(predictions.get('random_forest', 0) * 100) if predictions.get('random_forest') else None,
            'xgboost': round(predictions.get('xgboost', 0) * 100) if predictions.get('xgboost') else None
        } if ensemble.is_model_loaded() else None
    }
    
    set_cached(url, result)
    return jsonify(result)

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    success = feedback_system.add_feedback(
        url=data.get('url', ''),
        model_verdict=data.get('model_verdict', ''),
        user_verdict=data.get('user_verdict', ''),
        user_comment=data.get('comment', '')
    )
    
    if success:
        logger.info(f"Feedback: {data.get('url')[:50]}...")
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 500

@app.route('/admin/feedbacks')
def admin_feedbacks():
    try:
        df = feedback_system.get_all_feedback(limit=100)
        if df.empty:
            return '<h1>📋 Отзывы</h1><p>Пока нет отзывов</p><a href="/">Главная</a>'
        
        html = '<h1>📋 Отзывы</h1><a href="/">← Главная</a><table border="1">'
        html += '<tr><th>ID</th><th>URL</th><th>Модель</th><th>Пользователь</th><th>Комментарий</th><th>Дата</th></tr>'
        
        for _, row in df.iterrows():
            style = 'style="background-color: #ffebee;"' if row['model_verdict'] != row['user_verdict'] else ''
            html += f'<tr {style}><td>{row["id"]}</td><td>{row["url"][:80]}</td>'
            html += f'<td>{row["model_verdict"]}</td><td style="color: {"red" if row["user_verdict"]=="dangerous" else "green"}">{row["user_verdict"]}</td>'
            html += f'<td>{row.get("user_comment", "-")}</td><td>{row["timestamp"][:19]}</td></tr>'
        
        html += '</table>'
        stats = feedback_system.get_stats()
        html += f'<hr><h3>📊 Статистика</h3><p>Отзывов: {stats["total_feedback"]}</p><p>Расхождений: {stats["mismatches"]}</p><p>Точность: {stats["accuracy_estimate"]}%</p>'
        return html
    except Exception as e:
        return f"<h1>Ошибка</h1><p>{e}</p>"

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
