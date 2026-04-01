import os
from pathlib import Path

class Config:
    """Централизованная конфигурация"""
    
    # Базовые пути
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / 'data'
    PROCESSED_DATA_DIR = DATA_DIR / 'processed'
    RAW_DATA_DIR = DATA_DIR / 'raw'
    MODELS_DIR = BASE_DIR / 'ml' / 'models'
    SRC_DIR = BASE_DIR / 'src'
    
    # База данных
    FEEDBACK_DB_PATH = DATA_DIR / 'feedback.db'
    
    # Признаки (15 признаков)
    FEATURE_COLS = [
        'url_length', 'num_dots', 'num_hyphens', 'num_slashes', 'num_params',
        'has_ip', 'has_https', 'has_login', 'has_verify', 'has_account',
        'has_cp.php', 'has_admin', 'is_shortened', 'domain_length'
    ]
    
    @classmethod
    def init_dirs(cls):
        """Создание директорий"""
        for dir_path in [cls.DATA_DIR, cls.PROCESSED_DATA_DIR, 
                         cls.RAW_DATA_DIR, cls.MODELS_DIR]:
            dir_path.mkdir(exist_ok=True)
