# Инструкция по обновлению voice-transcription-amocrm

После развёртывания защищённой версии mcp-amocrm-server необходимо обновить сервис `voice-transcription-amocrm`.

## Проблема

`voice-transcription-amocrm` использует следующие эндпоинты mcp-amocrm-server:
- `GET /api/chat/recent?limit=100`
- `GET /api/chat/lead/{lead_id}?limit=100`

После внедрения авторизации эти запросы будут возвращать **401 Unauthorized**.

## Решение

### Шаг 1: Добавить переменную окружения

В Railway Dashboard → voice-transcription-amocrm → Variables добавить:

```bash
AMOCRM_API_KEY=<тот же ключ, что в API_SECRET_KEY сервиса mcp-amocrm-server>
```

⚠️ **Важно**: используйте ТОЧНО ТОТ ЖЕ ключ, что задан в `API_SECRET_KEY` для mcp-amocrm-server.

### Шаг 2: Обновить код

Найдите в `voice-transcription-amocrm/main.py` функцию `_fetch_chat_json` (или аналогичную):

#### До (без авторизации):

```python
async def _fetch_chat_json(path: str) -> dict:
    url = f"{CHAT_STORAGE_URL}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.warning(f"Chat API {path} → {resp.status}")
                return {}
            return await resp.json()
```

#### После (с авторизацией):

```python
AMOCRM_API_KEY = os.getenv("AMOCRM_API_KEY", "")

async def _fetch_chat_json(path: str) -> dict:
    url = f"{CHAT_STORAGE_URL}{path}"
    headers = {}
    
    # Добавляем авторизацию, если ключ настроен
    if AMOCRM_API_KEY:
        headers["Authorization"] = f"Bearer {AMOCRM_API_KEY}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, 
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 401:
                logger.error(f"❌ Chat API {path} → 401 Unauthorized. Check AMOCRM_API_KEY")
                return {}
            if resp.status != 200:
                logger.warning(f"Chat API {path} → {resp.status}")
                return {}
            return await resp.json()
```

### Шаг 3: Коммит и деплой

```bash
git add main.py
git commit -m "feat: добавлена авторизация для mcp-amocrm-server API"
git push origin main
```

Railway автоматически задеплоит изменения.

### Шаг 4: Проверка

После деплоя проверьте логи `voice-transcription-amocrm`:
- ✅ Должны отсутствовать ошибки `401 Unauthorized`
- ✅ Должны успешно загружаться чат-сообщения

Если видите ошибки:
1. Проверьте, что `AMOCRM_API_KEY` задан в Railway
2. Проверьте, что ключ совпадает с `API_SECRET_KEY` в mcp-amocrm-server
3. Проверьте, что новая версия кода задеплоена

## Альтернативный вариант (используя X-API-Key)

Вместо `Authorization: Bearer` можно использовать `X-API-Key`:

```python
if AMOCRM_API_KEY:
    headers["X-API-Key"] = AMOCRM_API_KEY
```

Оба варианта работают одинаково.

## Откат (если что-то пошло не так)

Если после обновления возникли проблемы:

1. **Временное решение**: откатить mcp-amocrm-server на предыдущую версию
   - В Railway Dashboard → mcp-amocrm-server → Deployments
   - Найти предыдущий деплой и нажать "Redeploy"

2. **Постоянное решение**: исправить конфигурацию и переразвернуть оба сервиса

## Тестирование локально

Перед деплоем можно протестировать локально:

```bash
# В терминале 1: запустить mcp-amocrm-server с API_SECRET_KEY
cd mcp-amocrm-server
export API_SECRET_KEY="test_key_12345"
export MCP_PATH_SECRET="test_secret"
export AMOCRM_SUBDOMAIN="your_subdomain"
export AMOCRM_ACCESS_TOKEN="your_token"
python3 app.py

# В терминале 2: проверить авторизацию
curl -H "Authorization: Bearer test_key_12345" \
  http://localhost:8000/api/chat/recent

# Должен вернуть данные (или пустой список), а не 401
```

## Контакты

При возникновении проблем обращайтесь к владельцу репозитория.
