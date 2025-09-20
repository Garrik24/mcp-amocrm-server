# 🚀 Пошаговый деплой на Railway

## Вариант А: Через веб-интерфейс (самый простой)

### 1. Подготовка GitHub репозитория
```bash
# Если еще не связал с GitHub:
cd ~/Projects/mcp-amocrm-server
git remote add origin https://github.com/YOUR_USERNAME/mcp-amocrm-server.git
git push -u origin main
```

### 2. Деплой через Railway.app
1. Открой [railway.app](https://railway.app)
2. Нажми **"Start a New Project"**
3. Выбери **"Deploy from GitHub repo"**
4. Выбери свой репозиторий `mcp-amocrm-server`
5. Railway автоматически обнаружит Python проект

### 3. Настройка переменных окружения
В настройках проекта добавь:
```
AMOCRM_CLIENT_ID=your_client_id
AMOCRM_CLIENT_SECRET=your_secret
AMOCRM_SUBDOMAIN=your_subdomain
AMOCRM_ACCESS_TOKEN=your_token
```

---

## Вариант Б: Через CLI (интерактивный)

### 1. Авторизация в Railway
```bash
cd ~/Projects/mcp-amocrm-server
railway login
# Откроется браузер для авторизации
```

### 2. Инициализация проекта
```bash
railway init
# Выбери "Create new project"
# Введи название: amocrm-mcp-server
```

### 3. Деплой
```bash
railway up
# Подожди завершения деплоя
```

### 4. Получение URL
```bash
railway domain
# Создаст домен вида: amocrm-mcp-server.up.railway.app
```

---

## Вариант В: Heroku (альтернатива)

### 1. Установка Heroku CLI
```bash
brew install heroku/brew/heroku
heroku login
```

### 2. Создание приложения
```bash
cd ~/Projects/mcp-amocrm-server
heroku create your-amocrm-server
```

### 3. Настройка переменных
```bash
heroku config:set AMOCRM_CLIENT_ID=your_id
heroku config:set AMOCRM_CLIENT_SECRET=your_secret
heroku config:set AMOCRM_SUBDOMAIN=your_subdomain
```

### 4. Деплой
```bash
git push heroku main
```

---

## После деплоя

### 1. Проверка работы
```bash
curl https://your-domain.up.railway.app/
# Должен вернуть JSON со статусом
```

### 2. Получение OpenAPI схемы
```bash
curl https://your-domain.up.railway.app/openapi.json
```

### 3. Обновление ChatGPT конфигурации
Замени в файле `chatgpt_openapi.json`:
```json
"url": "https://your-domain.up.railway.app"
```

---

## 🎯 Быстрый старт (2 клика)

**Самый простой способ:**

1. **Загрузи код на GitHub:**
   - Создай новый репозиторий на GitHub
   - Запуши туда код проекта

2. **Подключи к Railway:**
   - Открой [railway.app](https://railway.app) 
   - "New Project" → "Deploy from GitHub"
   - Выбери репозиторий → Railway сделает всё сам

**Готово!** Railway выдаст тебе публичный URL типа:
`https://mcp-amocrm-server.up.railway.app`
