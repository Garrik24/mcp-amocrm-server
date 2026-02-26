from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
import os
import aiohttp
import yarl
import logging
import time
import json
import asyncio
from urllib.parse import quote
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AmoCRM MCP Server",
    description="Сервер для интеграции с AmoCRM API через долгосрочный токен",
    version="3.0.0"
)

# Добавляем CORS для ChatGPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничьте до chatgpt.com
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация из переменных окружения
AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN", "stavgeo26")
AMOCRM_ACCESS_TOKEN = os.getenv("AMOCRM_ACCESS_TOKEN")  # Долгосрочный токен

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
            "events": "/api/events",
            "tasks": "/api/tasks",
            "contacts": "/api/contacts",
            "notes": "/api/notes/{entity_type}/{entity_id}",
            "v4_proxy": "/api/v4-proxy/{path}",
            "webhooks": "/webhooks/receive"
        }
    }

@app.get("/health")
async def health_check():
    """Health check для Railway"""
    return {"status": "healthy", "timestamp": int(time.time())}

def build_url_with_params(base_url: str, params: Dict = None) -> str:
    """
    Строит URL с query-параметрами:
    - сохраняет [] в ключах (filter[type][])
    - безопасно кодирует значения
    - поддерживает повторяющиеся ключи через list
    """
    if not params:
        return base_url

    parts = []
    for key, value in params.items():
        if value is None:
            continue

        safe_key = quote(str(key), safe="[]")
        if isinstance(value, list):
            for item in value:
                if item is None:
                    continue
                parts.append(f"{safe_key}={quote(str(item), safe='')}")
        else:
            parts.append(f"{safe_key}={quote(str(value), safe='')}")

    if parts:
        return f"{base_url}?{'&'.join(parts)}"
    return base_url


async def make_amocrm_request(endpoint: str, method: str = "GET", data: Dict = None, params: Dict = None):
    """Выполняет запрос к AmoCRM API"""
    if not AMOCRM_ACCESS_TOKEN:
        raise HTTPException(status_code=400, detail="AmoCRM access token не настроен")

    # Строим URL вручную, чтобы скобки [] не кодировались
    base_url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru{endpoint}"
    url = build_url_with_params(base_url, params) if method.upper() == "GET" else base_url

    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    logger.info(f"AmoCRM request: {method} {url}")

    async with aiohttp.ClientSession() as session:
        try:
            if method.upper() == "GET":
                async with session.get(yarl.URL(url, encoded=True), headers=headers) as response:
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

@app.get("/api/leads/loss-reasons")
async def get_loss_reasons(authorization: Optional[str] = Header(None)):
    """Получение списка причин потери сделок"""
    try:
        result = await make_amocrm_request("/api/v4/leads/loss_reasons", "GET")
        return result
    except Exception as e:
        logger.error(f"Ошибка получения причин потери: {str(e)}")
        return {"error": str(e), "status": "error"}


# ========== СОБЫТИЯ (ПОЧТА, ЗВОНКИ, ЧАТЫ) ==========

@app.get("/api/events")
async def get_events(
    request: Request,
    type: Optional[str] = Query(None, description="Тип события: incoming_mail_message, outgoing_mail_message, incoming_call, outgoing_call, incoming_chat_message"),
    date_from: Optional[str] = Query(None, description="Начало периода (ISO или unix timestamp)"),
    date_to: Optional[str] = Query(None, description="Конец периода (ISO или unix timestamp)"),
    limit: Optional[int] = Query(50, description="Количество записей (по умолчанию 50)"),
    page: Optional[int] = Query(1, description="Номер страницы"),
    authorization: Optional[str] = Header(None)
):
    """Получение событий из amoCRM (почта, звонки, чаты)"""
    try:
        params = {}
        type_values: List[str] = []

        if type:
            type_values.extend([t.strip() for t in type.split(",") if t.strip()])

        # Поддержка формата amoCRM filter[type][]=...
        type_values.extend([v for v in request.query_params.getlist("filter[type][]") if v])

        # Поддержка индексированного формата filter[type][0]=...
        for key, value in request.query_params.multi_items():
            if key.startswith("filter[type][") and key.endswith("]") and value:
                type_values.append(value)

        if type_values:
            params["filter[type][]"] = type_values

        if date_from:
            # Если пришла ISO дата, конвертируем в unix timestamp
            try:
                ts = int(date_from)
            except ValueError:
                from datetime import datetime
                dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                ts = int(dt.timestamp())
            params["filter[created_at][from]"] = ts
        if date_to:
            try:
                ts = int(date_to)
            except ValueError:
                from datetime import datetime
                dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                ts = int(dt.timestamp())
            params["filter[created_at][to]"] = ts
        params["limit"] = min(limit, 100)
        params["page"] = page

        result = await make_amocrm_request("/api/v4/events", "GET", params=params)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения событий: {str(e)}")
        return {"error": str(e), "status": "error"}


# ========== ЗАДАЧИ ==========

@app.get("/api/tasks")
async def get_tasks(
    is_completed: Optional[int] = Query(None, description="0 — не выполнены, 1 — выполнены"),
    responsible_user_id: Optional[int] = Query(None, description="ID ответственного"),
    limit: Optional[int] = Query(50, description="Количество задач"),
    page: Optional[int] = Query(1, description="Номер страницы"),
    authorization: Optional[str] = Header(None)
):
    """Получение задач из amoCRM"""
    try:
        params = {"limit": min(limit, 250), "page": page}
        if is_completed is not None:
            params["filter[is_completed]"] = is_completed
        if responsible_user_id:
            params["filter[responsible_user_id]"] = responsible_user_id

        result = await make_amocrm_request("/api/v4/tasks", "GET", params=params)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения задач: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.post("/api/tasks")
async def create_task_endpoint(request: Request, authorization: Optional[str] = Header(None)):
    """Создание задачи в amoCRM"""
    try:
        body = await request.json()
        # Если пришёл одиночный объект — оборачиваем в массив
        if isinstance(body, dict):
            body = [body]
        result = await make_amocrm_request("/api/v4/tasks", "POST", data=body)
        return result
    except Exception as e:
        logger.error(f"Ошибка создания задачи: {str(e)}")
        return {"error": str(e), "status": "error"}


# ========== КОНТАКТЫ (расширенный) ==========

@app.get("/api/contacts")
async def get_contacts_endpoint(
    query: Optional[str] = Query(None, description="Поиск по имени/телефону/email"),
    limit: Optional[int] = Query(50, description="Количество контактов"),
    with_leads: Optional[bool] = Query(False, description="Подтянуть связанные сделки"),
    page: Optional[int] = Query(1, description="Номер страницы"),
    authorization: Optional[str] = Header(None)
):
    """Получение контактов из amoCRM с возможностью поиска"""
    try:
        params = {"limit": min(limit, 250), "page": page}
        if query:
            params["query"] = query
        if with_leads:
            params["with"] = "leads"

        result = await make_amocrm_request("/api/v4/contacts", "GET", params=params)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения контактов: {str(e)}")
        return {"error": str(e), "status": "error"}


# ========== ПРИМЕЧАНИЯ (NOTES) ==========

@app.get("/api/notes/{entity_type}/{entity_id}")
async def get_notes(
    entity_type: str,
    entity_id: int,
    limit: Optional[int] = Query(50, description="Количество примечаний"),
    page: Optional[int] = Query(1, description="Номер страницы"),
    note_type: Optional[str] = Query(None, description="Тип примечания (common, call_in, call_out, sms_in, sms_out и т.д.)"),
    authorization: Optional[str] = Header(None)
):
    """Получение примечаний к сущности (leads, contacts, companies)"""
    try:
        params = {"limit": min(limit, 250), "page": page}
        if note_type:
            params["filter[note_type]"] = note_type

        endpoint = f"/api/v4/{entity_type}/{entity_id}/notes"
        result = await make_amocrm_request(endpoint, "GET", params=params)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения примечаний: {str(e)}")
        return {"error": str(e), "status": "error"}


# ========== УНИВЕРСАЛЬНЫЙ ПРОКСИ К amoCRM API v4 ==========

@app.api_route("/api/v4-proxy/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def proxy_amocrm_v4(path: str, request: Request, authorization: Optional[str] = Header(None)):
    """
    Прямой прокси к amoCRM API v4.
    Пример: GET /api/v4-proxy/events?filter[type][]=incoming_mail_message
    проксируется в GET https://stavgeo26.amocrm.ru/api/v4/events?filter[type][]=incoming_mail_message
    """
    try:
        endpoint = f"/api/v4/{path}"
        method = request.method.upper()
        params = dict(request.query_params)
        data = None

        if method in ("POST", "PATCH"):
            try:
                data = await request.json()
            except Exception:
                data = None

        result = await make_amocrm_request(endpoint, method, data=data, params=params if method == "GET" else None)
        return result
    except Exception as e:
        logger.error(f"Ошибка прокси v4/{path}: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.get("/api/report/deals")
async def get_deals_report(
    query: Optional[str] = Query(None, description="Поисковый запрос для фильтрации сделок"),
    created_at_from: Optional[int] = Query(None, description="Дата создания (Unix Timestamp) с которой нужно начать поиск"),
    updated_at_from: Optional[int] = Query(None, description="Дата обновления (Unix Timestamp) с которой нужно начать поиск"),
    status_id: Optional[int] = Query(None, description="ID статуса сделки (этапа воронки)"),
    pipeline_id: Optional[int] = Query(None, description="ID воронки продаж"),
    limit: Optional[int] = Query(250, description="Количество сделок за один запрос (макс 250)"),
    page: Optional[int] = Query(1, description="Номер страницы для пагинации"),
    authorization: Optional[str] = Header(None)
):
    """
    Получение отчета по сделкам.
    Позволяет фильтровать сделки по дате создания, обновления, статусу, воронке и поисковому запросу.
    Теперь с поддержкой пагинации - можно получить до 250 сделок за раз.
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
        params["with"] = "contacts,companies,loss_reason"
        params["limit"] = min(limit, 250)  # Максимум 250 (ограничение AmoCRM)
        params["page"] = page
        
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

# ========== MCP ENDPOINTS ДЛЯ CHATGPT CONNECTORS ==========

# Хранилище активных SSE соединений
active_connections: Dict[str, asyncio.Queue] = {}

@app.get("/mcp")
async def mcp_root():
    """Корневой MCP endpoint для проверки доступности"""
    return {
        "name": "amocrm-mcp-server",
        "version": "3.0.0",
        "protocol": "mcp",
        "endpoints": {
            "sse": "/mcp/sse",
            "messages": "/mcp/messages"
        },
        "status": "active"
    }

@app.get("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    """SSE endpoint для ChatGPT MCP Connector"""
    async def event_generator():
        # Создаем уникальный ID для соединения
        connection_id = str(time.time())
        queue = asyncio.Queue()
        active_connections[connection_id] = queue
        
        logger.info(f"MCP SSE: Новое подключение {connection_id}")
        
        try:
            # Отправляем приветственное сообщение
            init_message = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "amocrm-mcp-server",
                        "version": "3.0.0"
                    }
                }
            }
            yield f"data: {json.dumps(init_message)}\n\n"
            
            # Держим соединение открытым
            while True:
                if await request.is_disconnected():
                    logger.info(f"MCP SSE: Клиент отключился {connection_id}")
                    break
                    
                try:
                    # Ждем сообщения из очереди с таймаутом
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Отправляем keep-alive каждые 30 секунд
                    yield f": keep-alive\n\n"
                    
        except Exception as e:
            logger.error(f"MCP SSE ошибка: {str(e)}")
        finally:
            # Очищаем соединение
            if connection_id in active_connections:
                del active_connections[connection_id]
            logger.info(f"MCP SSE: Соединение закрыто {connection_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/mcp/messages")
async def mcp_messages_endpoint(request: Request):
    """Endpoint для обработки MCP сообщений от ChatGPT"""
    try:
        body = await request.json()
        logger.info(f"MCP Message: {body}")
        
        # Обрабатываем запрос в зависимости от метода
        method = body.get("method")
        params = body.get("params", {})
        
        if method == "tools/list":
            # Возвращаем список доступных инструментов
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "get_account",
                            "description": "Получить информацию об аккаунте AmoCRM",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "search_contacts",
                            "description": "Поиск контактов по email или телефону",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Email, телефон или имя для поиска"
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "create_lead",
                            "description": "Создать сделку в AmoCRM",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Название сделки"
                                    },
                                    "price": {
                                        "type": "number",
                                        "description": "Бюджет сделки"
                                    }
                                },
                                "required": ["name"]
                            }
                        },
                        {
                            "name": "get_events",
                            "description": "Получить события из amoCRM (почта, звонки, чаты). Используйте для сводки входящей/исходящей почты, звонков и сообщений.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "description": "Тип события: incoming_mail_message, outgoing_mail_message, incoming_call, outgoing_call, incoming_chat_message. Можно несколько через запятую."
                                    },
                                    "date_from": {
                                        "type": "string",
                                        "description": "Начало периода (ISO дата или unix timestamp)"
                                    },
                                    "date_to": {
                                        "type": "string",
                                        "description": "Конец периода (ISO дата или unix timestamp)"
                                    },
                                    "limit": {
                                        "type": "number",
                                        "description": "Количество записей (по умолчанию 50)",
                                        "default": 50
                                    }
                                }
                            }
                        },
                        {
                            "name": "get_tasks",
                            "description": "Получить список задач из amoCRM. Используйте для показа задач на день, невыполненных задач, задач конкретного пользователя.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "is_completed": {
                                        "type": "number",
                                        "description": "0 — не выполнены, 1 — выполнены. Если не указано — все задачи."
                                    },
                                    "responsible_user_id": {
                                        "type": "number",
                                        "description": "ID ответственного пользователя"
                                    },
                                    "limit": {
                                        "type": "number",
                                        "description": "Количество задач (по умолчанию 50)",
                                        "default": 50
                                    }
                                }
                            }
                        },
                        {
                            "name": "create_task",
                            "description": "Создать задачу в amoCRM. Привязывается к сделке или контакту.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "Текст задачи"
                                    },
                                    "complete_till": {
                                        "type": "number",
                                        "description": "Срок выполнения (Unix timestamp)"
                                    },
                                    "entity_id": {
                                        "type": "number",
                                        "description": "ID сделки или контакта"
                                    },
                                    "entity_type": {
                                        "type": "string",
                                        "description": "Тип сущности: leads или contacts",
                                        "enum": ["leads", "contacts"]
                                    },
                                    "task_type_id": {
                                        "type": "number",
                                        "description": "Тип задачи (1 — Связаться, 2 — Встреча). По умолчанию 1."
                                    },
                                    "responsible_user_id": {
                                        "type": "number",
                                        "description": "ID ответственного"
                                    }
                                },
                                "required": ["text", "complete_till", "entity_id", "entity_type"]
                            }
                        },
                        {
                            "name": "get_contacts",
                            "description": "Получить контакты из amoCRM с поиском по имени, телефону или email. Может подтянуть связанные сделки.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Поисковый запрос (имя, телефон, email)"
                                    },
                                    "limit": {
                                        "type": "number",
                                        "description": "Количество контактов (по умолчанию 50)",
                                        "default": 50
                                    },
                                    "with_leads": {
                                        "type": "boolean",
                                        "description": "Подтянуть связанные сделки (true/false)",
                                        "default": False
                                    }
                                }
                            }
                        },
                        {
                            "name": "get_notes",
                            "description": "Получить примечания (notes) к сделке, контакту или компании. Используйте для чтения истории переписки и комментариев.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "entity_type": {
                                        "type": "string",
                                        "description": "Тип сущности: leads, contacts или companies",
                                        "enum": ["leads", "contacts", "companies"]
                                    },
                                    "entity_id": {
                                        "type": "number",
                                        "description": "ID сущности"
                                    },
                                    "limit": {
                                        "type": "number",
                                        "description": "Количество примечаний (по умолчанию 50)",
                                        "default": 50
                                    }
                                },
                                "required": ["entity_type", "entity_id"]
                            }
                        },
                        {
                            "name": "amocrm_request",
                            "description": "Универсальный запрос к amoCRM API v4. Используйте для любого endpoint amoCRM, который не покрыт другими инструментами. Все params передаются напрямую в query string запроса к amoCRM.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "method": {
                                        "type": "string",
                                        "description": "HTTP метод: GET, POST, PATCH, DELETE",
                                        "enum": ["GET", "POST", "PATCH", "DELETE"]
                                    },
                                    "path": {
                                        "type": "string",
                                        "description": "Путь к API amoCRM, например: /api/v4/events, /api/v4/tasks, /api/v4/contacts"
                                    },
                                    "params": {
                                        "type": "object",
                                        "description": "Query-параметры запроса. Например: {\"filter[type][]\": \"incoming_mail_message\", \"limit\": 5}"
                                    },
                                    "body": {
                                        "type": "object",
                                        "description": "JSON тело запроса для POST/PATCH"
                                    }
                                },
                                "required": ["method", "path"]
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            # Вызов конкретного инструмента
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            result = None
            
            if tool_name == "get_account":
                result = await make_amocrm_request("/api/v4/account")
            
            elif tool_name == "search_contacts":
                result = await make_amocrm_request(
                    "/api/v4/contacts",
                    "GET",
                    params={"query": tool_args.get("query"), "limit": 10}
                )
            
            elif tool_name == "create_lead":
                lead_data = [{
                    "name": tool_args.get("name"),
                    "price": tool_args.get("price", 0)
                }]
                result = await make_amocrm_request(
                    "/api/v4/leads",
                    "POST",
                    data=lead_data
                )

            elif tool_name == "get_events":
                params = {}
                event_type = tool_args.get("type")
                if event_type:
                    types = [t.strip() for t in event_type.split(",")]
                    for i, t in enumerate(types):
                        params[f"filter[type][{i}]"] = t
                date_from = tool_args.get("date_from")
                if date_from:
                    try:
                        ts = int(date_from)
                    except (ValueError, TypeError):
                        from datetime import datetime as dt_cls
                        d = dt_cls.fromisoformat(str(date_from).replace("Z", "+00:00"))
                        ts = int(d.timestamp())
                    params["filter[created_at][from]"] = ts
                date_to = tool_args.get("date_to")
                if date_to:
                    try:
                        ts = int(date_to)
                    except (ValueError, TypeError):
                        from datetime import datetime as dt_cls
                        d = dt_cls.fromisoformat(str(date_to).replace("Z", "+00:00"))
                        ts = int(d.timestamp())
                    params["filter[created_at][to]"] = ts
                params["limit"] = tool_args.get("limit", 50)
                result = await make_amocrm_request("/api/v4/events", "GET", params=params)

            elif tool_name == "get_tasks":
                params = {"limit": tool_args.get("limit", 50)}
                if "is_completed" in tool_args and tool_args["is_completed"] is not None:
                    params["filter[is_completed]"] = tool_args["is_completed"]
                if tool_args.get("responsible_user_id"):
                    params["filter[responsible_user_id]"] = tool_args["responsible_user_id"]
                result = await make_amocrm_request("/api/v4/tasks", "GET", params=params)

            elif tool_name == "create_task":
                task_data = [{
                    "text": tool_args["text"],
                    "complete_till": tool_args["complete_till"],
                    "entity_id": tool_args["entity_id"],
                    "entity_type": tool_args["entity_type"],
                    "task_type_id": tool_args.get("task_type_id", 1),
                }]
                if tool_args.get("responsible_user_id"):
                    task_data[0]["responsible_user_id"] = tool_args["responsible_user_id"]
                result = await make_amocrm_request("/api/v4/tasks", "POST", data=task_data)

            elif tool_name == "get_contacts":
                params = {"limit": tool_args.get("limit", 50)}
                if tool_args.get("query"):
                    params["query"] = tool_args["query"]
                if tool_args.get("with_leads"):
                    params["with"] = "leads"
                result = await make_amocrm_request("/api/v4/contacts", "GET", params=params)

            elif tool_name == "get_notes":
                entity_type = tool_args["entity_type"]
                entity_id = tool_args["entity_id"]
                params = {"limit": tool_args.get("limit", 50)}
                result = await make_amocrm_request(
                    f"/api/v4/{entity_type}/{entity_id}/notes",
                    "GET",
                    params=params
                )

            elif tool_name == "amocrm_request":
                req_method = tool_args.get("method", "GET").upper()
                req_path = tool_args.get("path", "").rstrip("/")
                req_params = tool_args.get("params", {})
                req_body = tool_args.get("body")

                # Нормализуем путь для сравнения
                norm_path = req_path
                if norm_path.startswith("/api/v4/"):
                    norm_path = "/api/" + norm_path[8:]
                elif not norm_path.startswith("/api/"):
                    norm_path = "/api/" + norm_path.lstrip("/")

                # Роутинг через внутреннюю логику для известных эндпоинтов
                # чтобы упрощённые параметры (type, is_completed, query)
                # правильно транслировались в формат amoCRM (filter[type][] и т.д.)
                if norm_path == "/api/events" and req_method == "GET":
                    ev_params = {}
                    event_type = req_params.get("type")
                    if event_type:
                        types = [t.strip() for t in str(event_type).split(",")]
                        for i, t in enumerate(types):
                            ev_params[f"filter[type][{i}]"] = t
                    date_from = req_params.get("date_from")
                    if date_from:
                        try:
                            ts = int(date_from)
                        except (ValueError, TypeError):
                            from datetime import datetime as dt_cls
                            d = dt_cls.fromisoformat(str(date_from).replace("Z", "+00:00"))
                            ts = int(d.timestamp())
                        ev_params["filter[created_at][from]"] = ts
                    date_to = req_params.get("date_to")
                    if date_to:
                        try:
                            ts = int(date_to)
                        except (ValueError, TypeError):
                            from datetime import datetime as dt_cls
                            d = dt_cls.fromisoformat(str(date_to).replace("Z", "+00:00"))
                            ts = int(d.timestamp())
                        ev_params["filter[created_at][to]"] = ts
                    ev_params["limit"] = req_params.get("limit", 50)
                    ev_params["page"] = req_params.get("page", 1)
                    # Прокидываем любые filter[*] параметры напрямую
                    for k, v in req_params.items():
                        if k.startswith("filter["):
                            ev_params[k] = v
                    result = await make_amocrm_request("/api/v4/events", "GET", params=ev_params)

                elif norm_path == "/api/tasks" and req_method == "GET":
                    t_params = {
                        "limit": req_params.get("limit", 50),
                        "page": req_params.get("page", 1)
                    }
                    if "is_completed" in req_params and req_params["is_completed"] is not None:
                        t_params["filter[is_completed]"] = req_params["is_completed"]
                    if req_params.get("responsible_user_id"):
                        t_params["filter[responsible_user_id]"] = req_params["responsible_user_id"]
                    for k, v in req_params.items():
                        if k.startswith("filter["):
                            t_params[k] = v
                    result = await make_amocrm_request("/api/v4/tasks", "GET", params=t_params)

                elif norm_path == "/api/contacts" and req_method == "GET":
                    c_params = {
                        "limit": req_params.get("limit", 50),
                        "page": req_params.get("page", 1)
                    }
                    if req_params.get("query"):
                        c_params["query"] = req_params["query"]
                    if req_params.get("with_leads"):
                        c_params["with"] = "leads"
                    if req_params.get("with"):
                        c_params["with"] = req_params["with"]
                    for k, v in req_params.items():
                        if k.startswith("filter["):
                            c_params[k] = v
                    result = await make_amocrm_request("/api/v4/contacts", "GET", params=c_params)

                else:
                    # Универсальный passthrough к amoCRM API v4
                    if not req_path.startswith("/api/v4"):
                        if req_path.startswith("/api/"):
                            req_path = "/api/v4/" + req_path[5:]
                        elif req_path.startswith("/"):
                            req_path = "/api/v4" + req_path
                        else:
                            req_path = "/api/v4/" + req_path

                    data = None
                    if req_method in ("POST", "PATCH") and req_body:
                        data = req_body if isinstance(req_body, list) else [req_body]

                    result = await make_amocrm_request(
                        req_path,
                        req_method,
                        data=data,
                        params=req_params if req_method == "GET" else None
                    )

            if result is None:
                result = {"error": f"Unknown tool: {tool_name}"}

            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }
        
        else:
            # Неизвестный метод
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            
    except Exception as e:
        logger.error(f"MCP Messages ошибка: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": body.get("id", None),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

