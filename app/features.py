import re
import numpy as np
from urllib.parse import urlparse
import math
from collections import Counter

FEATURE_NAMES = [
    'url_length', 'domain_length', 'path_length', 'has_ip', 'tld_length',
    'has_https', 'num_subdomains', 'num_params', 'num_fragments',
    'digit_ratio', 'special_char_ratio', 'has_login', 'has_bank', 'has_pay',
    'suspicious_tld', 'typo_squatting', 'homograph', 'entropy'
]

def extract_features(url):
    """Извлечение всех признаков из URL"""
    parsed = urlparse(url)
    features = {}
    
    # Базовые признаки
    features['url_length'] = len(url)
    features['domain_length'] = len(parsed.netloc)
    features['path_length'] = len(parsed.path)
    features['has_ip'] = 1 if re.match(r'\d+\.\d+\.\d+\.\d+', parsed.netloc) else 0
    
    # TLD длина
    tld_parts = parsed.netloc.split('.')
    features['tld_length'] = len(tld_parts[-1]) if len(tld_parts) > 1 else 0
    
    # HTTPS
    features['has_https'] = 1 if parsed.scheme == 'https' else 0
    
    # Поддомены
    features['num_subdomains'] = len(tld_parts) - 2 if len(tld_parts) > 2 else 0
    
    # Параметры и фрагменты
    features['num_params'] = len(parsed.query.split('&')) if parsed.query else 0
    features['num_fragments'] = 1 if parsed.fragment else 0
    
    # Соотношение цифр
    digits = sum(c.isdigit() for c in url)
    features['digit_ratio'] = digits / len(url) if len(url) > 0 else 0
    
    # Спецсимволы
    special_chars = sum(1 for c in url if not c.isalnum() and c not in ':/?.=_-')
    features['special_char_ratio'] = special_chars / len(url) if len(url) > 0 else 0
    
    # Ключевые слова
    url_lower = url.lower()
    features['has_login'] = 1 if 'login' in url_lower else 0
    features['has_bank'] = 1 if any(word in url_lower for word in ['bank', 'sber', 'tinkoff']) else 0
    features['has_pay'] = 1 if any(word in url_lower for word in ['pay', 'payment', 'paypal']) else 0
    
    # Подозрительные TLD
    suspicious_tlds = ['.xyz', '.top', '.tk', '.ml', '.club', '.online']
    features['suspicious_tld'] = 1 if any(tld in url_lower for tld in suspicious_tlds) else 0
    
    # Оппечатка
    popular_domains = ['google', 'facebook', 'yandex', 'sberbank']
    features['typo_squatting'] = 1 if any(domain in url_lower and domain not in parsed.netloc 
                                          for domain in popular_domains) else 0
    
    # Гомоглифы (кириллица)
    homoglyph_set = 'аеосухрс'
    features['homograph'] = 1 if any(c in homoglyph_set for c in url) else 0
    
    # Энтропия URL
    prob_dist = [url.count(c) / len(url) for c in set(url)]
    features['entropy'] = -sum(p * math.log2(p) for p in prob_dist if p > 0)
    
    return features

def extract_features_batch(urls):
    """Извлечение признаков для списка URL"""
    return np.array([list(extract_features(url).values()) for url in urls])
