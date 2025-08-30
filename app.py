from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import aiohttp
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AmoCRM MCP Server",
    description="Сервер для интеграции с AmoCRM API через долгосрочный токен",
    version="3.0.0"
)

# Конфигурация из переменных окружения
AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN", "stavgeo26")
AMOCRM_ACCESS_TOKEN = os.getenv("AMOCRM_ACCESS_TOKEN")  # Долгосрочный токен

# Модели данных
class EntityRequest(BaseModel):
    entity_type: str = Field(..., description="Тип сущности: leads, contacts, companies, tasks, customers")
    method: str = Field(..., description="Метод: get, create, update, delete")
    entity_id: Optional[int] = Field(None, description="ID сущности для get/update/delete")
    data: Optional[Dict[str, Any]] = Field(None, description="Данные для create/update")
    params: Optional[Dict[str, Any]] = Field(None, description="Параметры запроса для get")

class PipelineRequest(BaseModel):
    pipeline_id: Optional[int] = Field(None, description="ID воронки")

class WebhookData(BaseModel):
    leads: Optional[Dict] = None
    contacts: Optional[Dict] = None
    companies: Optional[Dict] = None

# Вспомогательные функции
async def make_amocrm_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    token: Optional[str] = None
):
    """Универсальная функция для запросов к AmoCRM API"""
    # Используем переданный токен или токен из переменных окружения
    access_token = token or AMOCRM_ACCESS_TOKEN
    
    if not access_token:
        raise HTTPException(status_code=401, detail="Токен доступа не настроен")
    
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
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    return await handle_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при запросе к AmoCRM: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка соединения с AmoCRM: {str(e)}")

async def handle_response(response):
    """Обработка ответа от AmoCRM"""
    if response.status == 204:  # No content (успешное удаление)
        return {"status": "success"}
    elif response.status == 401:
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
    token_status = "настроен" if AMOCRM_ACCESS_TOKEN else "не настроен"
    return {
        "status": "active",
        "service": "AmoCRM MCP Server",
        "version": "3.0.0",
        "subdomain": AMOCRM_SUBDOMAIN,
        "token_status": token_status,
        "endpoints": {
            "account": "/api/account",
            "entities": "/api/entities",
            "pipelines": "/api/pipelines",
            "users": "/api/users",
            "custom_fields": "/api/custom_fields",
            "webhooks": "/webhooks/receive"
        }
    }

@app.get("/api/account")
async def get_account(authorization: Optional[str] = Header(None)):
    """Получение информации об аккаунте"""
    # Извлекаем токен из заголовка, если передан
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    result = await make_amocrm_request(
        method="GET",
        endpoint="/api/v4/account",
        params={"with": "amojo_id,amojo_rights,users_groups,task_types,version,entity_names"},
        token=token
    )
    return result

@app.post("/api/entities")
async def handle_entities(request: EntityRequest, authorization: Optional[str] = Header(None)):
    """Универсальный эндпоинт для работы с сущностями AmoCRM"""
    # Извлекаем токен из заголовка, если передан
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    # Проверка типа сущности
    valid_entities = ["leads", "contacts", "companies", "tasks", "customers", "catalogs", "custom_fields"]
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
            params=request.params,
            token=token
        )
        
    elif request.method == "create":
        if not request.data:
            raise HTTPException(status_code=400, detail="Данные для создания не предоставлены")
        
        result = await make_amocrm_request(
            method="POST",
            endpoint=f"/api/v4/{request.entity_type}",
            data=request.data,
            token=token
        )
        
    elif request.method == "update":
        if not request.entity_id or not request.data:
            raise HTTPException(status_code=400, detail="ID сущности и данные обязательны для обновления")
        
        result = await make_amocrm_request(
            method="PATCH",
            endpoint=f"/api/v4/{request.entity_type}/{request.entity_id}",
            data=request.data,
            token=token
        )
        
    elif request.method == "delete":
        if not request.entity_id:
            raise HTTPException(status_code=400, detail="ID сущности обязателен для удаления")
        
        result = await make_amocrm_request(
            method="DELETE",
            endpoint=f"/api/v4/{request.entity_type}/{request.entity_id}",
            token=token
        )
    else:
        raise HTTPException(status_code=400, detail="Неверный метод. Доступны: get, create, update, delete")
    
    return result

@app.get("/api/pipelines")
async def get_pipelines(pipeline_id: Optional[int] = None, authorization: Optional[str] = Header(None)):
    """Получение воронок продаж"""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    if pipeline_id:
        endpoint = f"/api/v4/leads/pipelines/{pipeline_id}"
    else:
        endpoint = "/api/v4/leads/pipelines"
    
    result = await make_amocrm_request(
        method="GET",
        endpoint=endpoint,
        token=token
    )
    return result

@app.get("/api/users")
async def get_users(user_id: Optional[int] = None, authorization: Optional[str] = Header(None)):
    """Получение пользователей"""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    if user_id:
        endpoint = f"/api/v4/users/{user_id}"
    else:
        endpoint = "/api/v4/users"
    
    result = await make_amocrm_request(
        method="GET",
        endpoint=endpoint,
        token=token
    )
    return result

@app.get("/api/custom_fields/{entity_type}")
async def get_custom_fields(entity_type: str, authorization: Optional[str] = Header(None)):
    """Получение пользовательских полей для типа сущности"""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    valid_entities = ["leads", "contacts", "companies", "customers"]
    if entity_type not in valid_entities:
        raise HTTPException(status_code=400, detail=f"Неверный тип сущности. Доступны: {valid_entities}")
    
    result = await make_amocrm_request(
        method="GET",
        endpoint=f"/api/v4/{entity_type}/custom_fields",
        token=token
    )
    return result

@app.post("/webhooks/receive")
async def receive_webhook(data: WebhookData):
    """Приём вебхуков от AmoCRM"""
    logger.info(f"Получен вебхук: {data}")
    
    # Здесь можно добавить обработку вебхуков
    # Например, сохранение в БД, отправка уведомлений и т.д.
    
    return {"status": "received"}
