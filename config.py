import os
from pathlib import Path

class Config:
    """Централизованная конфигурация"""
    
    # Пути
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / 'data'
    MODELS_DIR = BASE_DIR / 'models'
    LOG_DIR = BASE_DIR / 'logs'
    STATIC_DIR = BASE_DIR / 'static'
    TEMPLATES_DIR = BASE_DIR / 'templates'
    
    # Модели
    RANDOM_FOREST_PATH = MODELS_DIR / 'random_forest.pkl'
    XGBOOST_PATH = MODELS_DIR / 'xgboost.pkl'
    
    # Веса моделей в ансамбле (сумма = 1)
    MODEL_WEIGHTS = {
        'random_forest': 0.5,
        'xgboost': 0.5
    }
    
    # Пороги
    DANGEROUS_THRESHOLD = 0.7
    SUSPICIOUS_THRESHOLD = 0.4
    
    # Признаки
    FEATURE_COLS = [
        'url_length', 'num_dots', 'num_hyphens', 'num_slashes', 'num_params',
        'has_ip', 'has_https', 'has_login', 'has_verify', 'has_account',
        'has_cp.php', 'has_admin', 'is_shortened', 'domain_length'
    ]
    
    # Кэширование
    CACHE_TTL_HOURS = 1
    CACHE_MAX_SIZE = 10000
    
    # Подозрительные паттерны
    SUSPICIOUS_WORDS = ['login', 'verify', 'account', 'secure', 'banking', 
                        'payment', 'update', 'confirm']
    
    URL_SHORTENERS = ['bit.ly', 'goo.gl', 'tinyurl', 'cutt.ly']
    
    POPULAR_BRANDS = ['paypal', 'google', 'apple', 'amazon', 'facebook', 'sberbank']
    
    LEGITIMATE_DOMAINS = ['sberbank.ru', 'google.com', 'apple.com', 'paypal.com']
    
    SUSPICIOUS_TLDS = ['.xyz', '.top', '.club', '.online', '.site', '.tk', '.ml']
    
    # Сервер
    PORT = int(os.environ.get("PORT", 5000))
    HOST = '0.0.0.0'
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    
    @classmethod
    def init_dirs(cls):
        """Создание директорий"""
        for dir_path in [cls.DATA_DIR, cls.MODELS_DIR, cls.LOG_DIR]:
            dir_path.mkdir(exist_ok=True)
        (cls.DATA_DIR / 'raw').mkdir(exist_ok=True)
        (cls.DATA_DIR / 'processed').mkdir(exist_ok=True)
