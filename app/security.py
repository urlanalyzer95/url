<<<<<<< HEAD
from urllib.parse import urlparse

def validate_url(url):
    try:
        result = urlparse(url)
        if not result.scheme or not result.netloc:
            return False, "�������⨬� URL"
        return True, ""
    except:
        return False, "�訡�� ���ᨭ��"
=======
def validate_url(url):  # ← 1 аргумент (НЕ метод класса!)
    """Валидация URL"""
    if len(url) > 2048:
        return False, "URL слишком длинный"
    if not all(c.isalnum() or c in ':/.-?_=' for c in url.replace('http://', '').replace('https://', '')):
        return False, "Недопустимые символы"
    return True, ""

def rate_limit(f):  # ← Декоратор (НЕ используется сейчас)
    return f

# Создаём объект security с функциями как атрибуты
security = type('Security', (), {
    'validate_url': validate_url,
    'rate_limit': rate_limit
})()
>>>>>>> b6847356964f7823f4c3543bf060216d754af748
