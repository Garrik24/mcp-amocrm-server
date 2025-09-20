#!/bin/bash

echo "🚀 Автоматический деплой AmoCRM сервера"
echo "======================================"

# Проверяем, что мы в правильной директории
if [[ ! -f "app.py" ]]; then
    echo "❌ Ошибка: Запустите скрипт из папки mcp-amocrm-server"
    exit 1
fi

echo "📦 Подготовка файлов для деплоя..."

# Обновляем requirements.txt
echo "fastapi>=0.110.0
uvicorn[standard]>=0.27.0
aiohttp>=3.9.5
pydantic>=2.8.0
python-dotenv>=1.0.0
python-multipart>=0.0.7" > requirements.txt

# Создаем .dockerignore
echo "venv/
.git/
__pycache__/
*.pyc
.env
.DS_Store" > .dockerignore

echo "✅ Файлы подготовлены!"

echo ""
echo "🎯 СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1️⃣  GITHUB (если еще не сделано):"
echo "   git add . && git commit -m 'Ready for deployment'"
echo "   git push origin main"
echo ""
echo "2️⃣  RENDER.COM (рекомендуется):"
echo "   - Открой https://render.com"
echo "   - New → Web Service → Connect GitHub"
echo "   - Выбери репозиторий: Garrik24/mcp-amocrm-server"
echo "   - Build Command: pip install -r requirements.txt"  
echo "   - Start Command: uvicorn app:app --host 0.0.0.0 --port \$PORT"
echo ""
echo "3️⃣  RAILWAY.APP (альтернатива):"
echo "   - Открой https://railway.app"
echo "   - New Project → Deploy from GitHub"
echo "   - Выбери репозиторий"
echo ""
echo "4️⃣  HEROKU (если есть аккаунт):"
echo "   heroku create your-amocrm-app"
echo "   git push heroku main"
echo ""
echo "5️⃣  DOCKER (локально):"
echo "   docker build -t amocrm-server ."
echo "   docker run -p 8000:8000 amocrm-server"
echo ""
echo "📋 После деплоя получишь URL типа:"
echo "   https://amocrm-server.onrender.com"
echo ""
echo "🤖 Используй этот URL в ChatGPT Custom GPT schema!"

# Показываем готовую схему для ChatGPT
echo ""
echo "📄 ГОТОВАЯ СХЕМА ДЛЯ CHATGPT:"
echo "   Файл: chatgpt_demo_schema.json"
echo "   Замени URL на реальный после деплоя"
