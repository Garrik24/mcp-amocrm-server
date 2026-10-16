# Безопасность API

## Защита REST API эндпоинтов

Начиная с версии 3.1.0, все REST API эндпоинты `/api/*` защищены обязательной авторизацией.

### Переменная окружения

```bash
API_SECRET_KEY=your_random_api_key_here_minimum_32_characters
```

**Важно:**
- Используйте криптографически стойкий случайный ключ длиной минимум 32 символа
- Если переменная не задана, сервер запустится, но **все запросы к `/api/*` будут отклонены** (fail closed)
- В логах будет предупреждение: `⚠️  API_SECRET_KEY не задан — все запросы к /api/* будут отклонены`

### Использование API

Клиент должен отправлять секретный ключ одним из двух способов:

#### Вариант 1: Bearer token (рекомендуется)

```bash
curl -H "Authorization: Bearer YOUR_SECRET_KEY" \
  https://mcp-amocrm-server-production.up.railway.app/api/account
```

#### Вариант 2: X-API-Key заголовок

```bash
curl -H "X-API-Key: YOUR_SECRET_KEY" \
  https://mcp-amocrm-server-production.up.railway.app/api/account
```

### Защищённые эндпоинты

Все эндпоинты под `/api/*` требуют авторизации:
- `/api/account`
- `/api/entities`
- `/api/pipelines`
- `/api/users`
- `/api/custom_fields`
- `/api/events`
- `/api/tasks`
- `/api/contacts`
- `/api/notes/{entity_type}/{entity_id}`
- `/api/v4-proxy/{path}`
- `/api/report/deals`
- `/api/chat/*` (lead, contact, recent, search, stats)

### Незащищённые эндпоинты

Следующие эндпоинты **не требуют** авторизации:

#### Служебные
- `/` - информация о сервисе
- `/health` - health check для Railway

#### Webhook приёмники
- `/webhooks/receive` - вебхуки от amoCRM
- `/webhooks/voice-relay` - ретранслятор вебхуков для voice-transcription

#### MCP эндпоинты
- `/{MCP_PATH_SECRET}/mcp*` - защищены секретным путем (отдельная переменная `MCP_PATH_SECRET`)

## Безопасность реализации

### Constant-time comparison

Для сравнения секретных ключей используется `hmac.compare_digest()`, что защищает от timing attacks.

### Fail closed

Если `API_SECRET_KEY` не задан, сервер:
1. Запускается успешно (не падает)
2. Пишет предупреждение в лог
3. Отклоняет **все** запросы к `/api/*` с кодом 503 Service Unavailable

Это предотвращает случайный запуск сервера без защиты.

## Миграция существующих клиентов

### Клиенты, требующие обновления

**voice-transcription-amocrm** использует следующие эндпоинты:
- `GET /api/chat/recent?limit=100`
- `GET /api/chat/lead/{lead_id}?limit=100`

**Требуемые изменения:**
1. Добавить переменную окружения `AMOCRM_API_KEY=<тот же ключ, что в mcp-amocrm-server>`
2. Обновить HTTP клиент для отправки заголовка:
```python
headers = {
    "Authorization": f"Bearer {os.getenv('AMOCRM_API_KEY')}"
}
```

### Клиенты, не требующие изменений

Следующие сервисы обращаются напрямую к amoCRM API, минуя mcp-amocrm-server:
- `geodesist-max`
- `kp-followup-service`
- `amocrm-spam-checker`

## Генерация безопасного ключа

### Python
```python
import secrets
api_key = secrets.token_urlsafe(48)
print(api_key)
```

### Bash
```bash
openssl rand -base64 48
```

### Node.js
```javascript
const crypto = require('crypto');
console.log(crypto.randomBytes(48).toString('base64'));
```

## Логирование

Middleware логирует:
- ✅ Успешные авторизованные запросы: `✅ Authorized request to /api/...`
- ❌ Неавторизованные попытки: `❌ Unauthorized request to /api/... from <IP>`
- ⚠️  Попытки работы без настроенного ключа

**Важно:** Сам секретный ключ **никогда не логируется**.
