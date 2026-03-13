FROM python:3.13-slim

WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Railway назначает порт через переменную $PORT
ENV PORT=8000
EXPOSE ${PORT}

# Команда запуска — используем shell form для подстановки $PORT
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT}
