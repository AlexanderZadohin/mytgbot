# Берём официальный образ Python
FROM python:3.12-slim

# Директория внутри контейнера
WORKDIR /app

# Чтобы Python не записывал .pyc и сразу логировал в консоль
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Копируем список зависимостей и ставим их
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем остальной код бота
COPY . .

# Команда по умолчанию — запуск бота
CMD ["python", "bot.py"]
