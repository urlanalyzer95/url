import re
import pandas as pd
from urllib.parse import urlparse
from typing import List, Dict
from config import Config

class FeatureExtractor:
    """Извлечение признаков из URL"""
    
    def __init__(self):
        self.feature_names = Config.FEATURE_COLS
    
    def extract_features(self, url: str) -> List[float]:
        """Извлекает признаки для одного URL"""
        url = str(url).lower().strip()
        
        features = []
        
        # Базовые признаки
        features.append(len(url))  # url_length
        features.append(url.count('.'))  # num_dots
        features.append(url.count('-'))  # num_hyphens
        features.append(url.count('/'))  # num_slashes
        features.append(len(re.findall(r'[?&]', url)))  # num_params
        
        # Безопасность
        features.append(1 if re.search(r'\d{1,3}(\.\d{1,3}){3}', url) else 0)  # has_ip
        features.append(1 if url.startswith('https') else 0)  # has_https
        
        # Подозрительные слова
        for word in Config.SUSPICIOUS_WORDS[:5]:  # login, verify, account, cp.php, admin
            features.append(1 if word in url else 0)
        
        # Сокращатели
        features.append(1 if any(s in url for s in Config.URL_SHORTENERS) else 0)
        
        # Домен
        try:
            domain = urlparse(url).netloc
            features.append(len(domain))  # domain_length
        except:
            features.append(0)
        
        return features
    
    def extract_features_df(self, urls: List[str]) -> pd.DataFrame:
        """Извлекает признаки для списка URL"""
        features_list = []
        for url in urls:
            features = self.extract_features(url)
            features_list.append(features)
        return pd.DataFrame(features_list, columns=self.feature_names)

# Глобальный экземпляр
feature_extractor = FeatureExtractor()

def extract_features(url: str) -> List[float]:
    return feature_extractor.extract_features(url)
