# AmoCRM MCP Server

Сервер для интеграции с AmoCRM API на базе FastAPI.

## 🔴 КРИТИЧЕСКИЕ ИЗМЕНЕНИЯ БЕЗОПАСНОСТИ

1. **Удалены все секретные данные из кода**
2. **Добавлена обязательная проверка переменных окружения**
3. **Создан .gitignore для защиты конфиденциальных данных**

## Установка и настройка

### 1. Клонирование репозитория
```bash
git clone <your-repo-url>
cd amocrm-mcp-server
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

Заполните переменные вашими данными:
- `AMOCRM_CLIENT_ID` - ID интеграции из AmoCRM
- `AMOCRM_CLIENT_SECRET` - Секретный ключ интеграции
- `AMOCRM_SUBDOMAIN` - Поддомен вашего аккаунта AmoCRM
- `REDIRECT_URI` - URL для callback (должен совпадать с настройками в AmoCRM)

### 4. Запуск сервера

Для локальной разработки:
```bash
uvicorn app:app --reload --port 8000
```

Для production (Railway/Heroku):
```bash
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

## API Эндпоинты

### Авторизация
- `GET /auth/authorize` - Получить ссылку для OAuth авторизации
- `GET /callback` - Обработка callback от AmoCRM
- `POST /auth/token` - Обмен кода на токены
- `POST /auth/refresh` - Обновление токенов

### Работа с данными
- `GET /api/account` - Информация об аккаунте
- `POST /api/entities` - Универсальный метод для работы с сущностями

### Вебхуки
- `POST /webhooks/receive` - Приём вебхуков от AmoCRM

## Новые функции

1. **Безопасное хранение токенов** с поддержкой сессий
2. **Автоматическое обновление токенов**
3. **Универсальный API для всех сущностей AmoCRM**
4. **Обработка ошибок и логирование**
5. **Поддержка вебхуков**
6. **Документация API** (доступна по адресу `/docs`)

## Безопасность

⚠️ **ВАЖНО**: 
- Никогда не коммитьте файл `.env` с реальными данными
- Используйте переменные окружения для всех секретных данных
- В production используйте Redis или БД для хранения токенов

## Деплой на Railway

1. Создайте новый проект на Railway
2. Подключите GitHub репозиторий
3. Добавьте переменные окружения в настройках проекта:
   - `AMOCRM_CLIENT_ID`
   - `AMOCRM_CLIENT_SECRET`
   - `AMOCRM_SUBDOMAIN`
   - `REDIRECT_URI`
4. Railway автоматически развернёт приложение

## Примеры использования

### Получение токена
```python
import requests

# 1. Получить ссылку для авторизации
response = requests.get("https://your-domain.com/auth/authorize")
auth_url = response.json()["auth_url"]
# Перейти по ссылке и авторизоваться

# 2. После редиректа получить session_id
# session_id будет в ответе callback
```

### Работа с сущностями
```python
# Получить список сделок
response = requests.post(
    "https://your-domain.com/api/entities",
    params={"session_id": "your_session_id"},
    json={
        "entity_type": "leads",
        "method": "get",
        "params": {"limit": 10}
    }
)
```

## Поддержка

При возникновении проблем создайте issue в репозитории.
