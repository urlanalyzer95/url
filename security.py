def validate_url(url):
    """Валидация URL"""
    if len(url) > 2048:
        return False, "URL слишком длинный"
    if not url.replace('http', '').replace('://', '').replace('.', '').replace('/', '').replace('-', '').replace('_', '').replace('?', '').replace('=', ''):
        return False, "Недопустимые символы"
    return True, ""

def rate_limit(f):
    """Декоратор rate limit (заглушка)"""
    return f

security = type('Security', (), {'validate_url': validate_url, 'rate_limit': rate_limit})()
