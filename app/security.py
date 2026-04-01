from urllib.parse import urlparse

def validate_url(url):
    try:
        result = urlparse(url)
        if not result.scheme or not result.netloc:
            return False, "Недопустимый URL"
        return True, ""
    except:
        return False, "Ошибка парсинга"
