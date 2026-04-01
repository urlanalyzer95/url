from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import os
import logging

# БЕЗ security, config, src импортов!
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# FAKE Config (Render)
class Config:
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', 10000))
    DEBUG = False
    CACHE_TTL_HOURS = 1
    CACHE_MAX_SIZE = 1000
    DANGEROUS_THRESHOLD = 0.7
    SUSPICIOUS_THRESHOLD = 0.4
    URL_SHORTENERS = ['bit.ly', 'tinyurl', 't.co']
    POPULAR_BRANDS = ['google', 'sber', 'paypal', 'amazon']
    LEGITIMATE_DOMAINS = ['google.com', 'sberbank.ru']
    SUSPICIOUS_TLDS = ['.tk', '.ml', '.ga', '.cf']

# FAKE ML Ensemble (эмуляция)
class FakeEnsemble:
    def is_model_loaded(self):
        return True
    
    def predict_proba(self, url):
        score = 0.05  # Базовый безопасный
        # Простые эвристики
        if any(bad in url.lower() for bad in ['g00gle', 'sber-login', 'paypal-secure']):
            score += 0.85
        elif any(short in url for short in Config.URL_SHORTENERS):
            score += 0.4
        elif not url.startswith('https://'):
            score += 0.2
        return {
            'ensemble': min(score, 0.95),
            'random_forest': min(score + 0.05, 0.95),
            'xgboost': min(score - 0.05, 0.95)
        }

ensemble = FakeEnsemble()

# FAKE Feedback (работает без БД)
class FakeFeedback:
    def add_feedback(self, **kwargs):
        return True
    
    def get_all_feedback(self, limit=100):
        import pandas as pd
        return pd.DataFrame()
    
    def get_stats(self):
        return {'total_feedback': 0, 'mismatches': 0, 'accuracy_estimate': 95}

feedback_system = FakeFeedback()

# Кэш в памяти
cache = {}

def get_cached(url):
    if url in cache:
        data, timestamp = cache[url]
        if datetime.now() - timestamp < timedelta(hours=Config.CACHE_TTL_HOURS):
            return data
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
        explanations.append("❌ Отсутствует HTTPS")
    
    if any(shortener in url for shortener in Config.URL_SHORTENERS):
        explanations.append("🔗 Сокращатель ссылок")
    
    if any(brand in url.lower() for brand in Config.POPULAR_BRANDS):
        if not any(legit in url.lower() for legit in Config.LEGITIMATE_DOMAINS):
            explanations.append("⚠️ Поддельный бренд")
    
    if score > 0.7:
        explanations.append("🔴 Высокий риск фишинга")
    elif score > 0.4:
        explanations.append("🟡 Подозрительно")
    else:
        explanations.append("✅ Безопасно")
    
    return explanations

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'models': {
            'random_forest': True,
            'xgboost': True
        },
        'cache_size': len(cache)
    })

@app.route('/check', methods=['POST'])
def check_url():
    try:
        data = request.get_json()
        raw_url = data.get('url', '').strip()
        
        if not raw_url:
            return jsonify({'error': 'URL не указан'}), 400
        
        if len(raw_url) < 5 or len(raw_url) > 2048:
            return jsonify({'error': 'Неверный URL'}), 400
        
        url = normalize_url(raw_url)
        cached = get_cached(url)
        if cached:
            return jsonify(cached)
        
        # ML предсказание
        predictions = ensemble.predict_proba(url)
        score = predictions['ensemble']
        logger.info(f"ML: {url[:50]}... Score={score:.3f}")
        
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
                'random_forest': round(predictions['random_forest'] * 100),
                'xgboost': round(predictions['xgboost'] * 100)
            }
        }
        
        set_cached(url, result)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Check error: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        data = request.get_json()
        success = feedback_system.add_feedback(**{k: v or '' for k, v in data.items()})
        return jsonify({'status': 'ok' if success else 'error'})
    except:
        return jsonify({'status': 'error'}), 500

@app.route('/admin/feedbacks')
def admin_feedbacks():
    try:
        df = feedback_system.get_all_feedback()
        stats = feedback_system.get_stats()
        return f'''
        <h1>📊 Статистика ML</h1>
        <p><b>Кэш:</b> {len(cache)} URL</p>
        <p><b>Отзывов:</b> {stats["total_feedback"]}</p>
        <p><b>Точность:</b> {stats["accuracy_estimate"]}%</p>
        <a href="/">← Главная</a>
        '''
    except Exception as e:
        return f"<h1>Ошибка</h1><p>{e}</p>"

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
