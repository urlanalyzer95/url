import re
from urllib.parse import urlparse

def extract_features(url):
    """Извлечение 14 признаков для ML"""
    url = str(url).lower().strip().rstrip('/')
    
    features = []
    # 1. Длина URL
    features.append(len(url))
    # 2. Кол-во точек
    features.append(url.count('.'))
    # 3. Тире
    features.append(url.count('-'))
    # 4. Слеши
    features.append(url.count('/'))
    # 5. Параметры (?&)
    features.append(len(re.findall(r'[?&]', url)))
    # 6. IP адрес
    features.append(1 if re.search(r'\d{1,3}(\.\d{1,3}){3}', url) else 0)
    # 7. HTTPS
    features.append(1 if url.startswith('https') else 0)
    # 8-12. Подозрительные слова
    for word in ['login', 'verify', 'account', 'cp.php', 'admin']:
        features.append(1 if word in url else 0)
    # 13. Сокращатель
    features.append(1 if any(s in url for s in ['bit.ly','goo.gl','tinyurl']) else 0)
    # 14. Длина домена
    domain = urlparse(url).netloc
    features.append(len(domain))
    
    return features