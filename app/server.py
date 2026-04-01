from flask import Flask, render_template, request, jsonify
import os
import sys
import re
import joblib
import pandas as pd
import xgboost as xgb
from urllib.parse import urlparse
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ========================================
# ML МОДЕЛИ (98% точность!)
# ========================================
model_rf = None
model_xgb = None
feature_columns = []

try:
    model_rf = joblib.load('ml/model_rf.pkl')
    model_xgb = joblib.load('ml/model_xgboost.pkl')
    with open('ml/feature_columns.txt', 'r') as f:
        feature_columns = [line.strip() for line in f]
    print("✅ RF + XGBoost (98%) загружены!", file=sys.stderr)
except Exception as e:
    print(f"⚠️ Модели: {e}", file=sys.stderr)

def extract_features(url):
    """14 признаков для ML"""
    url = str(url).lower().strip().rstrip('/')
    features = []
    features.append(len(url))  # длина
    features.append(url.count('.'))  # точки
    features.append(url.count('-'))  # тире
    features.append(url.count('/'))  # слеши
    features.append(len(re.findall(r'[?&]', url)))  # параметры
    features.append(1 if re.search(r'\d{1,3}(\.\d{1,3}){3}', url) else 0)  # IP
    features.append(1 if url.startswith('https') else 0)  # HTTPS
    for word in ['login', 'verify', 'account', 'cp.php', 'admin']:  # слова
        features.append(1 if word in url else 0)
    features.append(1 if any(s in url for s in ['bit.ly','goo.gl','tinyurl']) else 0)  # сокращатель
    domain = urlparse(url).netloc  # домен
    features.append(len(domain))
    return features

def ml_predict(url):
    """ML предсказание (XGBoost > RF)"""
    try:
        features = extract_features(url)
        X = pd.DataFrame([features], columns=feature_columns)
        
        if model_xgb:
            prob = model_xgb.predict_proba(X)[0][1]  # phishing вероятность
            print(f"XGBoost: {prob:.3f}", file=sys.stderr)
            return prob
        elif model_rf:
            prob = model_rf.predict_proba(X)[0][1]
            print(f"RF: {prob:.3f}", file=sys.stderr)
            return prob
    except Exception as e:
        print(f"ML error: {e}", file=sys.stderr)
    return 0.5

# ========================================
# ОСНОВНАЯ ЛОГИКА АНАЛИЗА
# ========================================
def compute_score(url):
    signals = []
    url_norm = url.lower().strip().rstrip('/')
    
    # ML (60% вес!)
    ml_prob = ml_predict(url_norm)
    signals.append((0.6, ml_prob))
    
    # Эвристики (по 5-10%)
    if len(url_norm) > 75: signals.append((0.08, 0.9))  # длинный URL
    if url_norm.count('.') > 3: signals.append((0.07, 0.85))  # много точек
    if any(word in url_norm for word in ['login','verify','account']): signals.append((0.10, 0.95))
    if 'http' not in url_norm: signals.append((0.05, 0.8))  # без протокола
    
    # Итоговый риск
    risk = sum(weight * prob for weight, prob in signals)
    return min(1.0, risk)

def save_feedback(url, model_verdict, user_verdict):
    """Сохранить отзыв пользователя"""
    conn = sqlite3.connect('data/feedback.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT, model_verdict TEXT, user_verdict TEXT, timestamp DATETIME
        )
    ''')
    conn.execute('INSERT INTO feedbacks (url, model_verdict, user_verdict, timestamp) VALUES (?, ?, ?, ?)',
                (url, model_verdict, user_verdict, datetime.now()))
    conn.commit()
    conn.close()

# ========================================
# ROUTES
# ========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'Введите URL'}), 400
    
    risk = compute_score(url)
    
    # Вердикт
    if risk > 0.8:
        verdict = '🔴 ОПАСНЫЙ (фишинг!)'
        color = 'danger'
    elif risk > 0.5:
        verdict = '🟡 ПОДОЗРИТЕЛЬНЫЙ'
        color = 'warning'
    else:
        verdict = '🟢 БЕЗОПАСНЫЙ'
        color = 'safe'
    
    return jsonify({
        'url': url,
        'risk': f'{risk:.1%}',
        'verdict': verdict,
        'color': color
    })

@app.route('/feedback', methods=['POST'])
def feedback():
    url = request.form.get('url')
    model_verdict = request.form.get('model_verdict')
    user_verdict = request.form.get('user_verdict')
    
    if url and user_verdict in ['dangerous', 'safe']:
        save_feedback(url, model_verdict, user_verdict)
        return jsonify({'status': 'saved'})
    
    return jsonify({'error': 'Invalid data'}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)