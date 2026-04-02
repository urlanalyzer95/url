from urllib.parse import urlparse

def validate_url(url):
    """Проверка валидности URL"""
    try:
        if not url or not isinstance(url, str):
            return False, "URL is required"
        
        result = urlparse(url)
        if not result.scheme or not result.netloc:
            return False, "Invalid URL format"
        
        # Проверка на опасные схемы
        if result.scheme not in ['http', 'https']:
            return False, "Only HTTP/HTTPS URLs are allowed"
        
        return True, ""
    except Exception as e:
        return False, f"Error parsing URL: {str(e)}"
