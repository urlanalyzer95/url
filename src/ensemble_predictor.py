import joblib
import numpy as np
import re
from urllib.parse import urlparse
from config import Config

class EnsemblePredictor:
    def __init__(self):
        self.random_forest = None
        self.xgboost = None
        self.feature_cols = Config.FEATURE_COLS
        self.is_loaded = False
        self.load_models()
    
    def load_models(self):
        """Загрузка моделей"""
        try:
            self.random_forest = joblib.load('ml/models/random_forest.pkl')
            # self.xgboost = joblib.load('ml/models/xgboost.pkl')
            self.is_loaded = self.random_forest is not None
        except:
            self.is_loaded = False
    
    def is_model_loaded(self):
        return self.is_loaded
    
    def extract_features(self, url):
        """Извлечение признаков"""
        features = np.zeros(len(self.feature_cols))
        
        # url_length
        features[0] = len(url)
        
        # num_dots, num_hyphens, num_slashes
        features[1] = url.count('.')
        features[2] = url.count('-')
        features[3] = url.count('/')
        
        # num_params
        features[4] = url.count('?') + url.count('&')
        
        # has_ip
        features[5] = 1 if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url) else 0
        
        # has_https
        features[6] = 1 if 'https' in url else 0
        
        # has_login, has_verify, has_account
        suspicious = ['login', 'verify', 'account', 'cp.php', 'admin']
        for i, word in enumerate(suspicious, 7):
            features[i] = 1 if word in url.lower() else 0
        
        # is_shortened
        features[12] = 1 if any(s in url for s in Config.URL_SHORTENERS) else 0
        
        # domain_length
        try:
            domain = urlparse(url).netloc
            features[13] = len(domain)
        except:
            features[13] = 0
            
        return features
    
    def predict_proba(self, url):
        """Предсказание вероятности"""
        if not self.is_loaded:
            return {'ensemble': 0.3, 'random_forest': 0.3, 'xgboost': None}
        
        features = self.extract_features(url).reshape(1, -1)
        rf_proba = self.random_forest.predict_proba(features)[0][1]
        
        return {
            'ensemble': rf_proba,
            'random_forest': rf_proba,
            'xgboost': None  # Пока не загружен
        }

# Глобальный экземпляр
ensemble = EnsemblePredictor()
