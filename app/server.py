from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from config import Config
from logger import logger
from security import security
from src.ensemble_predictor import ensemble
from src.feedback_system import FeedbackSystem
from urllib.parse import urlparse

app = Flask(__name__, 
            template_folder=str(Config.TEMPLATES_DIR),
            static_folder=str(Config.STATIC_DIR))

# Инициализация
Config.init_dirs()

# Кэш
cache = {}

# Система обратной связи
feedback_system = FeedbackSystem()

def get_cached(url):
    """Получить результат из кэша"""
    if url in cache:
        data, timestamp = cache[url]
        if datetime.now() - timestamp < timedelta(hours=Config.CACHE_TTL_HOURS):
            return data
        del cache[url]
    return None

def set_cached(url, data):
    """Сохранить результат в кэш"""
    if len(cache) > Config.CACHE_MAX_SIZE:
        oldest = min(cache.keys(), key=lambda k: cache[k][1])
        del cache[oldest]
    cache[url] = (data, datetime.now())

def normalize_url(url):
    """Нормализация URL"""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.lower().rstrip('/')

def get_explanations(url, score):
    """Получить объяснения для вердикта"""
    explanations = []
    
    if not url.startswith('https'):
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
        }
    })

@app.route('/check', methods=['POST'])
@security.rate_limit()
def check_url():
    """Проверка URL на фишинг"""
    data = request.json
    raw_url = data.get('url', '').strip()
    
    if not raw_url:
        return jsonify({'error': 'URL не указан'}), 400
    
    # Валидация
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
    
    # Проверка кэша
    cached = get_cached(url)
    if cached:
        return jsonify(cached)
    
    # Проверка через ансамбль моделей
    if ensemble.is_model_loaded():
        predictions = ensemble.predict_proba(url)
        score = predictions['ensemble']
        
        # Логируем детали
        logger.info(f"URL: {url[:50]}... | RF={predictions['random_forest']:.3f}, "
                   f"XGB={predictions['xgboost']:.3f}, Score={score:.3f}")
    else:
        # Если модели не загружены, используем эвристики
        logger.warning("Модели не загружены, используются эвристики")
        score = 0.3  # По умолчанию низкая вероятность
    
    # Определяем вердикт
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
    """Сбор обратной связи"""
    data = request.json
    
    success = feedback_system.add_feedback(
        url=data.get('url', ''),
        model_verdict=data.get('model_verdict', ''),
        user_verdict=data.get('user_verdict', ''),
        user_comment=data.get('comment', '')
    )
    
    if success:
        logger.info(f"Получен отзыв: {data.get('url')[:50]}... -> {data.get('user_verdict')}")
        return jsonify({'status': 'ok'})
    else:
        return jsonify({'status': 'error'}), 500

@app.route('/admin/feedbacks')
def admin_feedbacks():
    """Админка для просмотра отзывов"""
    try:
        df = feedback_system.get_all_feedback(limit=100)
        
        if df.empty:
            return '''
            <h1>📋 Отзывы</h1>
            <p>Пока нет отзывов</p>
            <p><a href="/">На главную</a></p>
            '''
        
        html = '<h1>📋 Отзывы</h1>'
        html += '<p><a href="/">← На главную</a></p>'
        html += '<table border="1" cellpadding="5">'
        html += '<tr><th>ID</th><th>URL</th><th>Модель</th><th>Пользователь</th><th>Комментарий</th><th>Дата</th></tr>'
        
        for _, row in df.iterrows():
            style = ''
            if row['model_verdict'] != row['user_verdict']:
                style = 'style="background-color: #ffebee;"'
            
            html += f'<tr {style}>'
            html += f'<td>{row["id"]}</td>'
            html += f'<td style="max-width: 400px; word-break: break-all;">{row["url"][:80]}</td>'
            html += f'<td>{row["model_verdict"]}</td>'
            html += f'<td style="color: {"red" if row["user_verdict"]=="dangerous" else "green"}">{row["user_verdict"]}</td>'
            html += f'<td>{row.get("user_comment", "-")}</td>'
            html += f'<td>{row["timestamp"][:19]}</td>'
            html += '</tr>'
        
        html += '</table>'
        
        stats = feedback_system.get_stats()
        html += f'''
        <hr>
        <h3>📊 Статистика</h3>
        <p>Всего отзывов: {stats["total_feedback"]}</p>
        <p>Расхождений: {stats["mismatches"]}</p>
        <p>Точность: {stats["accuracy_estimate"]}%</p>
        '''
        
        return html
        
    except Exception as e:
        return f"<h1>Ошибка</h1><p>{e}</p>"

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
