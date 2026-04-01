# Стабильный Python 3.12 (без проблем с 3.14)
FROM python:3.12-slim

# Рабочая директория
WORKDIR /app

# Копируем requirements и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаём директории
RUN mkdir -p data/processed data/ ml/models/

# Порт для Render
EXPOSE 10000

# Gunicorn для продакшена (PORT от Render)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} app.server:app"]
