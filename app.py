from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
import os
import aiohttp
import logging
import time
import asyncio
from typing import AsyncGenerator

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
API_TOKEN = os.getenv("API_TOKEN")  # Токен для защиты API (если задан)

# Глобальная проверка токена: включается только если задан API_TOKEN
@app.middleware("http")
async def api_token_guard(request: Request, call_next):
    if API_TOKEN:
        open_paths = {"/", "/health", "/docs", "/openapi.json"}
        if request.url.path not in open_paths:
            auth_hdr = request.headers.get("authorization", "")
            if not auth_hdr.startswith("Bearer "):
                return JSONResponse({"detail": "Missing Bearer token"}, status_code=401)
            token = auth_hdr.split(" ", 1)[1]
            if token != API_TOKEN:
                return JSONResponse({"detail": "Invalid token"}, status_code=401)
    response = await call_next(request)
    return response

# Модели данных
class EntityRequest(BaseModel):
    entity_type: str = Field(..., description="Тип сущности: leads, contacts, companies, tasks, customers")
    method: str = Field(..., description="Метод: get, create, update, delete")
    entity_id: Optional[int] = Field(None, description="ID сущности для get/update/delete")
    # AmoCRM v4 для создания поддерживает массив объектов, поэтому разрешаем и dict, и list[dict]
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(
        None,
        description="Данные для create/update. Разрешены object или array of objects (для v4 POST).",
    )
    params: Optional[Dict[str, Any]] = Field(None, description="Параметры запроса для get")

class WebhookData(BaseModel):
    leads: Optional[Dict[str, Any]] = None
    contacts: Optional[Dict[str, Any]] = None
    companies: Optional[Dict[str, Any]] = None

# Хранилище сессий в памяти (для примера)
sessions = {}

@app.get("/")
async def root():
    """Проверка статуса сервера"""
    return {
        "status": "active",
        "service": "AmoCRM MCP Server",
        "version": "3.0.0",
        "subdomain": AMOCRM_SUBDOMAIN,
        "token_status": "настроен" if AMOCRM_ACCESS_TOKEN else "не настроен",
        "endpoints": {
            "account": "/api/account",
            "entities": "/api/entities",
            "pipelines": "/api/pipelines",
            "users": "/api/users",
            "custom_fields": "/api/custom_fields",
            "webhooks": "/webhooks/receive"
        }
    }

@app.get("/health")
async def health_check():
    """Health check для Railway"""
    return {"status": "healthy", "timestamp": int(time.time())}

# ===== MCP SSE (минимальная совместимость) =====
async def sse_event_generator() -> AsyncGenerator[bytes, None]:
    # Простейший SSE "проверочный" поток: отдает ping раз в 15 секунд
    while True:
        yield b"event: ping\n"
        yield f"data: {{\"time\": {int(time.time())}}}\n\n".encode()
        await asyncio.sleep(15)

@app.get("/mcp/sse")
async def mcp_sse(request: Request):
    # Защита по API_TOKEN уже делает middleware
    return JSONResponse(content={"message": "SSE endpoint placeholder. Please use Make HTTP module for now."}, status_code=501)

async def make_amocrm_request(endpoint: str, method: str = "GET", data: Dict = None, params: Dict = None):
    """Выполняет запрос к AmoCRM API"""
    if not AMOCRM_ACCESS_TOKEN:
        raise HTTPException(status_code=400, detail="AmoCRM access token не настроен")
    
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru{endpoint}"
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            if method.upper() == "GET":
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 204:
                        return {"status": "no_content", "code": 204}
                    try:
                        return await response.json()
                    except Exception:
                        return {"code": response.status, "text": await response.text()}
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 204:
                        return {"status": "no_content", "code": 204}
                    try:
                        return await response.json()
                    except Exception:
                        return {"code": response.status, "text": await response.text()}
            elif method.upper() == "PATCH":
                async with session.patch(url, headers=headers, json=data) as response:
                    if response.status == 204:
                        return {"status": "no_content", "code": 204}
                    try:
                        return await response.json()
                    except Exception:
                        return {"code": response.status, "text": await response.text()}
            elif method.upper() == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status in (200, 202, 204):
                        # У AmoCRM при успешном удалении часто 204 и пустой ответ
                        return {"status": "deleted", "code": response.status}
                    try:
                        return await response.json()
                    except Exception:
                        return {"code": response.status, "text": await response.text()}
        except Exception as e:
            logger.error(f"Ошибка запроса к AmoCRM: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка запроса к AmoCRM: {str(e)}")

@app.get("/api/account")
async def get_account(authorization: Optional[str] = Header(None)):
    """Получение информации об аккаунте"""
    try:
        result = await make_amocrm_request("/api/v4/account")
        return result
    except Exception as e:
        logger.error(f"Ошибка получения аккаунта: {str(e)}")
        return {"error": str(e), "status": "error"}

@app.post("/api/entities")
async def handle_entities(request: EntityRequest, authorization: Optional[str] = Header(None)):
    """Универсальный эндпоинт для работы с сущностями AmoCRM"""
    try:
        # Формируем endpoint
        endpoint = f"/api/v4/{request.entity_type}"
        if request.entity_id:
            endpoint += f"/{request.entity_id}"
        
        # Выполняем запрос
        if request.method.lower() == "get":
            result = await make_amocrm_request(endpoint, "GET", params=request.params)
        elif request.method.lower() in ["post", "create"]:
            # Нормализуем формат: для POST ожидаем массив объектов
            payload = request.data
            if payload is None:
                payload = []
            if isinstance(payload, dict):
                payload = [payload]
            # Если создаём lead с встраиваемыми сущностями/кастомными полями — используем /leads/complex
            if request.entity_type == "leads":
                has_complex = any(
                    isinstance(it, dict) and (
                        "_embedded" in it or "custom_fields_values" in it
                    ) for it in payload
                )
                if has_complex and "/leads" in endpoint:
                    endpoint = "/api/v4/leads/complex"
            result = await make_amocrm_request(endpoint, "POST", data=payload)
        elif request.method.lower() in ["patch", "update"]:
            payload = request.data
            if payload is None:
                payload = []
            if isinstance(payload, dict):
                payload = [payload]
            result = await make_amocrm_request(endpoint, "PATCH", data=payload)
        elif request.method.lower() == "delete":
            result = await make_amocrm_request(endpoint, "DELETE")
        else:
            raise HTTPException(status_code=400, detail="Неподдерживаемый метод")
        
        return result
    except Exception as e:
        logger.error(f"Ошибка обработки сущности: {str(e)}")
        return {"error": str(e), "status": "error"}

@app.delete("/api/entities/{entity_type}/{entity_id}")
async def delete_entity(entity_type: str, entity_id: int, authorization: Optional[str] = Header(None)):
    """Удаление сущности напрямую через DELETE (рекомендуемый способ для AmoCRM v4)."""
    try:
        endpoint = f"/api/v4/{entity_type}/{entity_id}"
        result = await make_amocrm_request(endpoint, "DELETE")
        return result
    except Exception as e:
        logger.error(f"Ошибка удаления {entity_type}/{entity_id}: {str(e)}")
        return {"error": str(e), "status": "error"}

@app.post("/api/entities/{entity_type}/{entity_id}/delete")
async def delete_entity_via_post(entity_type: str, entity_id: int, authorization: Optional[str] = Header(None)):
    """Удаление сущности через POST-обёртку (на случай клиентов, где сложно вызвать DELETE)."""
    try:
        endpoint = f"/api/v4/{entity_type}/{entity_id}"
        result = await make_amocrm_request(endpoint, "DELETE")
        return result
    except Exception as e:
        logger.error(f"Ошибка удаления (POST wrap) {entity_type}/{entity_id}: {str(e)}")
        return {"error": str(e), "status": "error"}

@app.get("/api/pipelines")
async def get_pipelines(pipeline_id: Optional[int] = Query(None), authorization: Optional[str] = Header(None)):
    """Получение воронок продаж"""
    try:
        endpoint = "/api/v4/leads/pipelines"
        if pipeline_id:
            endpoint += f"/{pipeline_id}"
        
        result = await make_amocrm_request(endpoint, "GET")
        return result
    except Exception as e:
        logger.error(f"Ошибка получения воронок: {str(e)}")
        return {"error": str(e), "status": "error"}

@app.get("/api/users")
async def get_users(user_id: Optional[int] = Query(None), authorization: Optional[str] = Header(None)):
    """Получение пользователей"""
    try:
        endpoint = "/api/v4/users"
        if user_id:
            endpoint += f"/{user_id}"
        
        result = await make_amocrm_request(endpoint, "GET")
        return result
    except Exception as e:
        logger.error(f"Ошибка получения пользователей: {str(e)}")
        return {"error": str(e), "status": "error"}

@app.get("/api/custom_fields/{entity_type}")
async def get_custom_fields(entity_type: str, authorization: Optional[str] = Header(None)):
    """Получение пользовательских полей для типа сущности"""
    try:
        endpoint = f"/api/v4/{entity_type}/custom_fields"
        result = await make_amocrm_request(endpoint, "GET")
        return result
    except Exception as e:
        logger.error(f"Ошибка получения полей: {str(e)}")
        return {"error": str(e), "status": "error"}

@app.post("/webhooks/receive")
async def receive_webhook(data: WebhookData):
    """Приём вебхуков от AmoCRM"""
    logger.info(f"Получен вебхук: {data}")
    
    # Здесь можно добавить обработку вебхуков
    # Например, сохранение в БД, отправка уведомлений и т.д.
    
    return {"status": "received"}


@app.get("/api/report/deals")
async def get_deals_report(
    query: Optional[str] = Query(None, description="Поисковый запрос для фильтрации сделок"),
    created_at_from: Optional[int] = Query(None, description="Дата создания (Unix Timestamp) с которой нужно начать поиск"),
    updated_at_from: Optional[int] = Query(None, description="Дата обновления (Unix Timestamp) с которой нужно начать поиск"),
    status_id: Optional[int] = Query(None, description="ID статуса сделки (этапа воронки)"),
    pipeline_id: Optional[int] = Query(None, description="ID воронки продаж"),
    authorization: Optional[str] = Header(None)
):
    """
    Получение отчета по сделкам.
    Позволяет фильтровать сделки по дате создания, обновления, статусу, воронке и поисковому запросу.
    """
    try:
        # Формируем параметры для AmoCRM API
        params = {}
        
        if query:
            params["query"] = query
        if created_at_from:
            params["filter[created_at][from]"] = created_at_from
        if updated_at_from:
            params["filter[updated_at][from]"] = updated_at_from
        if status_id:
            params["filter[statuses][0][status_id]"] = status_id
        if pipeline_id:
            params["filter[statuses][0][pipeline_id]"] = pipeline_id
        
        # Добавляем дополнительные поля для более подробной информации
        params["with"] = "contacts,companies"
        params["limit"] = 50
        
        result = await make_amocrm_request("/api/v4/leads", "GET", params=params)
        
        # Добавляем метаинформацию к ответу
        if "_embedded" in result and "leads" in result["_embedded"]:
            leads = result["_embedded"]["leads"]
            total_amount = sum(lead.get("price", 0) for lead in leads)
            
            return {
                "leads": leads,
                "summary": {
                    "total_count": len(leads),
                    "total_amount": total_amount,
                    "filters_applied": {
                        "query": query,
                        "created_at_from": created_at_from,
                        "updated_at_from": updated_at_from,
                        "status_id": status_id,
                        "pipeline_id": pipeline_id
                    }
                },
                "page_info": result.get("_page", {}),
                "_links": result.get("_links", {})
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Ошибка получения отчета по сделкам: {str(e)}")
        return {"error": str(e), "status": "error"}

@app.get("/api/events")
async def get_events(request: Request, authorization: Optional[str] = Header(None)):
    """Получение событий из AmoCRM. Все query-параметры проксируются в amoCRM API v4."""
    params = dict(request.query_params)
    params.setdefault("limit", 50)
    params.setdefault("page", 1)
    logger.info(f"GET /api/events params={params}")
    try:
        result = await make_amocrm_request("/api/v4/events", "GET", params=params)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения событий: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.get("/api/tasks")
async def get_tasks(request: Request, authorization: Optional[str] = Header(None)):
    """Получение задач из AmoCRM. Все query-параметры проксируются в amoCRM API v4."""
    params = dict(request.query_params)
    params.setdefault("limit", 50)
    params.setdefault("page", 1)
    logger.info(f"GET /api/tasks params={params}")
    try:
        result = await make_amocrm_request("/api/v4/tasks", "GET", params=params)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения задач: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.get("/api/contacts")
async def get_contacts(request: Request, authorization: Optional[str] = Header(None)):
    """Получение контактов из AmoCRM. Все query-параметры проксируются в amoCRM API v4."""
    params = dict(request.query_params)
    params.setdefault("limit", 50)
    params.setdefault("page", 1)
    logger.info(f"GET /api/contacts params={params}")
    try:
        result = await make_amocrm_request("/api/v4/contacts", "GET", params=params)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения контактов: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.get("/api/notes")
async def get_notes(request: Request, authorization: Optional[str] = Header(None)):
    """Получение примечаний из AmoCRM. Все query-параметры проксируются в amoCRM API v4."""
    params = dict(request.query_params)
    params.setdefault("limit", 50)
    params.setdefault("page", 1)
    logger.info(f"GET /api/notes params={params}")
    try:
        result = await make_amocrm_request("/api/v4/leads/notes", "GET", params=params)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения примечаний: {str(e)}")
        return {"error": str(e), "status": "error"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
