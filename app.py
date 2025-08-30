from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
import aiohttp
import json
import logging
from datetime import datetime, timedelta
import hashlib
import secrets
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AmoCRM MCP Server",
    description="Сервер для интеграции с AmoCRM API",
    version="2.0.0"
)

# Конфигурация из переменных окружения
AMOCRM_CLIENT_ID = os.getenv("AMOCRM_CLIENT_ID", "fa0b0e51-e31d-4bdc-834b-b5970e960ce3")
AMOCRM_CLIENT_SECRET = os.getenv("AMOCRM_CLIENT_SECRET", "IPDQVlRfkPvlAls2gSWbKiYxur1QdJZvDSHCjH5F3eNZ3A3KC5af6MTYfGm27khL")
AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN", "stavgeo26")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://mcp-amocrm-server-production.up.railway.app/callback")

# Логирование конфигурации (без секретов)
logger.info(f"Запуск сервера для поддомена: {AMOCRM_SUBDOMAIN}")

# Временное хранилище токенов (в продакшене использовать Redis/БД)
token_storage = {}

# Модели данных
class TokenRequest(BaseModel):
    auth_code: str = Field(..., description="Код авторизации от AmoCRM")

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh токен для обновления access токена")

class EntityRequest(BaseModel):
    entity_type: str = Field(..., description="Тип сущности: leads, contacts, companies, tasks")
    method: str = Field(..., description="Метод: get, create, update")
    entity_id: Optional[int] = Field(None, description="ID сущности для get/update")
    data: Optional[Dict[str, Any]] = Field(None, description="Данные для create/update")
    params: Optional[Dict[str, Any]] = Field(None, description="Параметры запроса")

class WebhookData(BaseModel):
    leads: Optional[Dict] = None
    contacts: Optional[Dict] = None
    companies: Optional[Dict] = None

# Вспомогательные функции
async def make_amocrm_request(
    method: str,
    endpoint: str,
    access_token: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None
):
    """Универсальная функция для запросов к AmoCRM API"""
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            if method == "GET":
                async with session.get(url, headers=headers, params=params) as response:
                    return await handle_response(response)
            elif method == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    return await handle_response(response)
            elif method == "PATCH":
                async with session.patch(url, headers=headers, json=data) as response:
                    return await handle_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при запросе к AmoCRM: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка соединения с AmoCRM: {str(e)}")

async def handle_response(response):
    """Обработка ответа от AmoCRM"""
    if response.status == 401:
        raise HTTPException(status_code=401, detail="Токен недействителен или истёк")
    elif response.status == 404:
        raise HTTPException(status_code=404, detail="Ресурс не найден")
    elif response.status >= 400:
        error_text = await response.text()
        raise HTTPException(status_code=response.status, detail=f"Ошибка AmoCRM: {error_text}")
    
    return await response.json()

# Эндпоинты
@app.get("/")
def root():
    """Проверка статуса сервера"""
    return {
        "status": "active",
        "service": "AmoCRM MCP Server",
        "version": "2.0.0",
        "subdomain": AMOCRM_SUBDOMAIN,
        "endpoints": {
            "auth": "/auth/authorize",
            "token": "/auth/token",
            "refresh": "/auth/refresh",
            "entities": "/api/entities",
            "account": "/api/account",
            "webhooks": "/webhooks/receive"
        }
    }

@app.get("/auth/authorize")
async def authorize():
    """Инициализация OAuth авторизации"""
    state = secrets.token_urlsafe(32)
    auth_url = (
        f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/oauth"
        f"?client_id={AMOCRM_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&state={state}"
    )
    return {
        "auth_url": auth_url,
        "state": state,
        "instruction": "Перейдите по ссылке для авторизации в AmoCRM"
    }

@app.get("/callback")
async def callback(code: str, state: Optional[str] = None):
    """Обработка callback от AmoCRM"""
    if not code:
        raise HTTPException(status_code=400, detail="Код авторизации не получен")
    
    # Обмен кода на токены
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/oauth2/access_token"
    data = {
        "client_id": AMOCRM_CLIENT_ID,
        "client_secret": AMOCRM_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise HTTPException(status_code=response.status, detail=f"Ошибка получения токена: {error_text}")
            
            tokens = await response.json()
            
            # Сохраняем токены (в продакшене использовать БД)
            session_id = secrets.token_urlsafe(32)
            token_storage[session_id] = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": datetime.now() + timedelta(seconds=tokens["expires_in"])
            }
            
            logger.info(f"Токены успешно получены для сессии {session_id}")
            
            return {
                "status": "success",
                "session_id": session_id,
                "expires_in": tokens["expires_in"],
                "message": "Авторизация успешна. Сохраните session_id для дальнейших запросов"
            }

@app.post("/auth/token")
async def get_token(request: TokenRequest):
    """Получение токенов по коду авторизации (альтернативный метод)"""
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/oauth2/access_token"
    
    data = {
        "client_id": AMOCRM_CLIENT_ID,
        "client_secret": AMOCRM_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": request.auth_code,
        "redirect_uri": REDIRECT_URI
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Ошибка получения токена: {error_text}")
                raise HTTPException(status_code=response.status, detail=f"Ошибка: {error_text}")
            
            result = await response.json()
            
            # Сохраняем токены
            session_id = secrets.token_urlsafe(32)
            token_storage[session_id] = {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "expires_at": datetime.now() + timedelta(seconds=result["expires_in"])
            }
            
            return {
                "status": "success",
                "session_id": session_id,
                "token_type": result["token_type"],
                "expires_in": result["expires_in"]
            }

@app.post("/auth/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """Обновление access токена"""
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/oauth2/access_token"
    
    data = {
        "client_id": AMOCRM_CLIENT_ID,
        "client_secret": AMOCRM_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": request.refresh_token,
        "redirect_uri": REDIRECT_URI
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise HTTPException(status_code=response.status, detail=f"Ошибка обновления токена: {error_text}")
            
            result = await response.json()
            
            # Обновляем токены в хранилище
            session_id = secrets.token_urlsafe(32)
            token_storage[session_id] = {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "expires_at": datetime.now() + timedelta(seconds=result["expires_in"])
            }
            
            return {
                "status": "success",
                "session_id": session_id,
                "expires_in": result["expires_in"]
            }

@app.get("/api/account")
async def get_account(session_id: str = "test"):
    """Получение информации об аккаунте"""
    if session_id not in token_storage:
        raise HTTPException(status_code=401, detail="Сессия не найдена")
    
    access_token = token_storage[session_id]["access_token"]
    
    result = await make_amocrm_request(
        method="GET",
        endpoint="/api/v4/account",
        access_token=access_token,
        params={"with": "amojo_id,amojo_rights,users_groups,task_types,version,entity_names"}
    )
    
    return result

@app.post("/api/entities")
async def handle_entities(request: EntityRequest, session_id: str = "test"):
    """Универсальный эндпоинт для работы с сущностями AmoCRM"""
    if session_id not in token_storage:
        raise HTTPException(status_code=401, detail="Сессия не найдена")
    
    access_token = token_storage[session_id]["access_token"]
    
    # Проверка типа сущности
    valid_entities = ["leads", "contacts", "companies", "tasks", "customers"]
    if request.entity_type not in valid_entities:
        raise HTTPException(status_code=400, detail=f"Неверный тип сущности. Доступны: {valid_entities}")
    
    # Обработка методов
    if request.method == "get":
        if request.entity_id:
            endpoint = f"/api/v4/{request.entity_type}/{request.entity_id}"
        else:
            endpoint = f"/api/v4/{request.entity_type}"
        
        result = await make_amocrm_request(
            method="GET",
            endpoint=endpoint,
            access_token=access_token,
            params=request.params
        )
        
    elif request.method == "create":
        if not request.data:
            raise HTTPException(status_code=400, detail="Данные для создания не предоставлены")
        
        result = await make_amocrm_request(
            method="POST",
            endpoint=f"/api/v4/{request.entity_type}",
            access_token=access_token,
            data=request.data
        )
        
    elif request.method == "update":
        if not request.entity_id or not request.data:
            raise HTTPException(status_code=400, detail="ID сущности и данные обязательны для обновления")
        
        result = await make_amocrm_request(
            method="PATCH",
            endpoint=f"/api/v4/{request.entity_type}/{request.entity_id}",
            access_token=access_token,
            data=request.data
        )
    else:
        raise HTTPException(status_code=400, detail="Неверный метод. Доступны: get, create, update")
    
    return result

@app.post("/webhooks/receive")
async def receive_webhook(data: WebhookData):
    """Приём вебхуков от AmoCRM"""
    logger.info(f"Получен вебхук: {data}")
    
    # Здесь можно добавить обработку вебхуков
    # Например, сохранение в БД, отправка уведомлений и т.д.
    
    return {"status": "received"}
