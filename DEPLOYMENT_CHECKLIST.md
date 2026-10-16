# Чеклист развёртывания защищённой версии

## Перед мержем PR

### 1. Генерация секретного ключа

Сгенерируйте криптографически стойкий ключ (минимум 32 символа):

```bash
# Python
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# или OpenSSL
openssl rand -base64 48

# или Node.js
node -e "console.log(require('crypto').randomBytes(48).toString('base64'))"
```

**Сохраните сгенерированный ключ** — он понадобится для двух сервисов.

### 2. Настройка mcp-amocrm-server

Railway Dashboard → AMOCRM project → mcp-amocrm-server → Variables

Добавить переменную:
- [ ] `API_SECRET_KEY` = `<сгенерированный ключ>`

### 3. Настройка voice-transcription-amocrm

Railway Dashboard → voice-transcription project → voice-transcription-amocrm → Variables

Добавить переменную:
- [ ] `AMOCRM_API_KEY` = `<тот же самый ключ>`

⚠️ **Важно**: ключи должны быть ОДИНАКОВЫМИ!

### 4. Обновление кода voice-transcription-amocrm

- [ ] Добавить заголовок `Authorization: Bearer` в функцию `_fetch_chat_json`
- [ ] Закоммитить и запушить изменения
- [ ] Дождаться успешного деплоя в Railway

Подробности в файле `MIGRATION_VOICE_TRANSCRIPTION.md`.

### 5. Локальное тестирование (опционально)

```bash
# Терминал 1: запустить mcp-amocrm-server
cd mcp-amocrm-server
export API_SECRET_KEY="<сгенерированный ключ>"
export MCP_PATH_SECRET="<ваш mcp secret>"
export AMOCRM_SUBDOMAIN="<ваш поддомен>"
export AMOCRM_ACCESS_TOKEN="<ваш токен>"
python3 app.py

# Терминал 2: тесты
cd mcp-amocrm-server
python3 test_api_auth.py

# Терминал 3: проверка API вручную
curl -H "Authorization: Bearer <сгенерированный ключ>" \
  http://localhost:8000/api/chat/recent
```

### 6. Проверка health check

- [ ] Убедиться, что `/health` доступен **без авторизации**:

```bash
curl https://mcp-amocrm-server-production.up.railway.app/health
```

Должен вернуть:
```json
{"status":"healthy","timestamp":1234567890}
```

## После мерджа PR

### 7. Автоматический деплой

Railway автоматически задеплоит изменения из `main`.

Проверить статус:
- [ ] Railway Dashboard → mcp-amocrm-server → Deployments → последний деплой SUCCESS

### 8. Проверка работоспособности

#### 8.1 Health check (без авторизации)

```bash
curl https://mcp-amocrm-server-production.up.railway.app/health
```

✅ Ожидается: `200 OK`, `{"status":"healthy",...}`

#### 8.2 API без токена (должен отказывать)

```bash
curl https://mcp-amocrm-server-production.up.railway.app/api/account
```

✅ Ожидается: `401 Unauthorized`

#### 8.3 API с токеном (должен работать)

```bash
curl -H "Authorization: Bearer <ваш ключ>" \
  https://mcp-amocrm-server-production.up.railway.app/api/account
```

✅ Ожидается: `200 OK` с данными amoCRM

#### 8.4 Вебхуки без авторизации (должны работать)

```bash
curl -X POST \
  https://mcp-amocrm-server-production.up.railway.app/webhooks/receive \
  -d "test=data"
```

✅ Ожидается: `200 OK`

### 9. Проверка voice-transcription-amocrm

Проверить логи в Railway Dashboard → voice-transcription-amocrm → Logs

- [ ] Нет ошибок `401 Unauthorized`
- [ ] Видны успешные запросы к `/api/chat/*`

### 10. Мониторинг (первые 24 часа)

- [ ] Проверять логи mcp-amocrm-server на наличие `❌ Unauthorized` от легитимных клиентов
- [ ] Проверять логи voice-transcription-amocrm на ошибки авторизации
- [ ] Убедиться, что health check продолжает работать (Railway использует его для проверки)

## Откат (если что-то пошло не так)

### Вариант 1: Откат mcp-amocrm-server

Railway Dashboard → mcp-amocrm-server → Deployments → выбрать предыдущий деплой → Redeploy

### Вариант 2: Откат через git

```bash
cd mcp-amocrm-server
git revert <commit-hash>
git push origin main
```

### Вариант 3: Временно отключить защиту

⚠️ **НЕ РЕКОМЕНДУЕТСЯ** (API останется открытым)

Railway Dashboard → mcp-amocrm-server → Variables → удалить `API_SECRET_KEY`

Сервер будет возвращать 503 для всех `/api/*` запросов.

## Контакты

При возникновении проблем обращайтесь к владельцу репозитория.

## Полезные ссылки

- PR: https://github.com/Garrik24/mcp-amocrm-server/pull/1
- Документация: `SECURITY.md`
- Инструкция по миграции: `MIGRATION_VOICE_TRANSCRIPTION.md`
- Railway: https://railway.app/
