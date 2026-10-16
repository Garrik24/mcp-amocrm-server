# 📤 КАК ОБНОВИТЬ GITHUB РЕПОЗИТОРИЙ

## 🎯 У ТЕБЯ 2 ВАРИАНТА:

### ⚡ ВАРИАНТ 1: Через веб-интерфейс (3 минуты)

1. **Открой:** https://github.com/Garrik24/mcp-amocrm-server
2. **Найди кнопку:** "Upload files" или "Add file" → "Upload files"
3. **Перетащи файлы** из папки `~/Projects/mcp-amocrm-server/` (кроме .git и venv)
4. **Или используй архив:** `~/Projects/amocrm-updated.tar.gz` 
5. **Commit changes**

### 🔑 ВАРИАНТ 2: Настрой git token (рекомендуется)

1. **Создай токен:**
   - Открой: https://github.com/settings/tokens
   - "Generate new token (classic)"
   - Выбери: "repo" (full control)
   - Скопируй токен

2. **Настрой git:**
```bash
cd ~/Projects/mcp-amocrm-server
git remote set-url origin https://ТВО_ТОКЕН@github.com/Garrik24/mcp-amocrm-server.git
git push origin main
```

## 🚀 ПОСЛЕ ОБНОВЛЕНИЯ GITHUB:

### Деплой на Railway:
1. **Открой:** [railway.app](https://railway.app)
2. **"New Project"** → **"Deploy from GitHub repo"**
3. **Выбери:** "Garrik24/mcp-amocrm-server"
4. **Deploy!**

### Получи URL:
- В Railway: "Domains" → "Generate Domain"
- Получишь: `https://твой-проект.up.railway.app`

### Обнови ChatGPT:
- В Actions Schema замени URL на полученный от Railway

## ✅ ГОТОВО!

После этого у тебя будет:
- ✅ Обновленный GitHub репозиторий
- ✅ Рабочий сервер на Railway  
- ✅ Работающий ChatGPT с AmoCRM

