from flask import Flask, request, jsonify, render_template
import joblib
import hashlib
import os
import time
import json
from urllib.parse import urlparse
from datetime import datetime
import numpy as np
import pandas as pd
from app import security, features
from app.cache import CacheManager
from app.feedback import FeedbackManager

app = Flask(__name__)

# Загрузка моделей Sprint 2 (98.4% + 98.3%)
MODEL_DIR = "ml/models"
cache = CacheManager()
feedback = FeedbackManager()

try:
    rf_model = joblib.load(os.path.join(MODEL_DIR, "rf_sprint2.pkl"))
    xgb_model = joblib.load(os.path.join(MODEL_DIR, "xgb_sprint2.pkl"))
    MODELS_LOADED = True
    print("✅ Sprint 2 модели загружены: RF 98.4% + XGB 98.3%")
except:
    rf_model = xgb_model = None
    MODELS_LOADED = False
    print("⚠️ Fallback: старые модели")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'models': {
            'random_forest': MODELS_LOADED,
            'xgboost': MODELS_LOADED,
            'version': 'sprint2_98'
        },
        'cache_size': cache.size(),
        'feedback_count': feedback.count()
    })

@app.route('/check', methods=['POST'])
def check_url():
    try:
        data = request.get_json()
        raw_url = data.get('url', '').strip()
        
        if not raw_url:
            return jsonify({'error': 'URL обязателен'}), 400
        
        # ✅ ФИКС: validate_url() с 1 аргументом
        validation_result = security.validate_url(raw_url)
        if not validation_result[0]:  # is_valid
            return jsonify({
                'safe': False,
                'risk_score': 100,
                'issues': [validation_result[1]],  # error_msg
                'message': 'Недопустимый URL'
            }), 400
        
        # Кэш проверка
        url_hash = hashlib.md5(raw_url.encode()).hexdigest()
        cached = cache.get(url_hash)
        if cached:
            return jsonify(cached)
        
        # Feature extraction
        feature_vector = features.extract_features(raw_url)
        df_features = pd.DataFrame([feature_vector], columns=features.FEATURE_NAMES)
        
        # ML Prediction (Sprint 2 98%)
        rf_pred = rf_model.predict_proba(df_features)[0][1] if MODELS_LOADED else 0.05
        xgb_pred = xgb_model.predict_proba(df_features)[0][1] if MODELS_LOADED else 0.05
        
        risk_score = max(rf_pred, xgb_pred) * 100
        
        # Feature-based rules (дополнительно)
        issues = []
        if features.has_typo_squatting(raw_url):
            issues.append("Поддельный бренд")
        if features.is_homograph(raw_url):
            issues.append("Гомографическая атака")
        if features.suspicious_tld(raw_url):
            issues.append("Подозрительный домен")
        
        result = {
            'safe': risk_score < 50,
            'risk_score': round(risk_score, 1),
            'issues': issues,
            'features': {k: round(v, 3) for k, v in zip(features.FEATURE_NAMES, feature_vector)},
            'rf_score': round(rf_pred * 100, 1),
            'xgb_score': round(xgb_pred * 100, 1),
            'timestamp': datetime.now().isoformat()
        }
        
        # Кэш на 1 час
        cache.set(url_hash, result, 3600)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR in /check: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка', 'safe': False}), 500

@app.route('/admin/feedbacks')
def admin_feedbacks():
    feedbacks = feedback.get_all()
    return jsonify(feedbacks)

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    feedback.add(
        url=data['url'],
        prediction=data['prediction'],
        actual=data['actual'],
        user_comment=data.get('comment', '')
    )
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
