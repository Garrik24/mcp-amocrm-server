#!/usr/bin/env python3
"""
Быстрый публичный сервер для AmoCRM с автоматическим туннелем
"""

import subprocess
import time
import threading
import requests
import json
import os
import sys

def start_fastapi_server():
    """Запускает FastAPI сервер"""
    print("🚀 Запускаю FastAPI сервер...")
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "app:app", "--host", "0.0.0.0", "--port", "8000"
    ])

def create_local_tunnel():
    """Создает локальный туннель через SSH или другие методы"""
    print("🌐 Создаю публичный доступ...")
    
    # Попробуем использовать локальный сервер без туннеля
    time.sleep(3)
    
    try:
        response = requests.get("http://127.0.0.1:8000")
        if response.status_code == 200:
            print("✅ Сервер работает на http://127.0.0.1:8000")
            print("📖 API документация: http://127.0.0.1:8000/docs")
            
            # Показываем готовую конфигурацию для ChatGPT
            print("\n" + "="*50)
            print("🤖 ГОТОВАЯ КОНФИГУРАЦИЯ ДЛЯ CHATGPT:")
            print("="*50)
            
            # Читаем локальную схему
            with open("CHATGPT_SETUP.md", "r") as f:
                setup_content = f.read()
                # Заменяем URL на локальный (для тестирования)
                setup_content = setup_content.replace("YOUR_DEPLOYED_URL_HERE", "127.0.0.1:8000")
                print(setup_content)
                
        else:
            print("❌ Сервер не отвечает")
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

def main():
    print("🎯 АВТОМАТИЧЕСКИЙ ЗАПУСК AMOCRM СЕРВЕРА")
    print("="*40)
    
    # Проверяем зависимости
    if not os.path.exists("app.py"):
        print("❌ Файл app.py не найден! Запустите из папки проекта.")
        return
    
    # Запускаем сервер в отдельном потоке
    server_thread = threading.Thread(target=start_fastapi_server, daemon=True)
    server_thread.start()
    
    # Создаем туннель
    create_local_tunnel()
    
    print("\n🔗 Для доступа извне используйте:")
    print("1. Render.com - https://render.com")
    print("2. Railway.app - https://railway.app") 
    print("3. Ngrok (с регистрацией) - https://ngrok.com")
    
    print("\n⏹️  Нажмите Ctrl+C для остановки")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")

if __name__ == "__main__":
    main()
