from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
import os
import aiohttp
import logging
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AmoCRM MCP Server",
    description="Сервер для интеграции с AmoCRM API через долгосрочный токен",
    version="3.0.0"
)

# CORS (разрешаем доступ для LLM/браузеров; при проде лучше ограничить домены)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
            "webhooks": "/webhooks/receive"
        }
    }

@app.get("/health")
async def health_check():
    """Health check для Railway"""
    return {"status": "healthy", "timestamp": int(time.time())}

@app.get("/debug/mcp-status")
async def mcp_status():
    """Проверка статуса MCP интеграции"""
    mcp_enabled = False
    mcp_error = None
    
    try:
        from mcp_server import app as mcp_app
        from mcp.server.sse import SseServerTransport
        mcp_enabled = True
    except Exception as e:
        mcp_error = str(e)
    
    return {
        "mcp_enabled": mcp_enabled,
        "mcp_error": mcp_error,
        "mcp_endpoint": "/mcp/sse" if mcp_enabled else None,
        "mcp_version": "1.17.0" if mcp_enabled else None
    }

# ===================== MCP over HTTP (для ChatGPT Connectors и любых клиентов MCP по сети) =====================
# Реализуем SSE/POST транспорт MCP по адресу /mcp
try:
    # Импортируем наш MCP-сервер (реестр инструментов) и HTTP транспорт из mcp
    from mcp_server import app as mcp_app
    from mcp.server.sse import SseServerTransport, TransportSecuritySettings

    # Создаем транспорт SSE
    security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    sse_transport = SseServerTransport(endpoint="/messages", security_settings=security)

    # Создаем ASGI приложение которое обрабатывает /mcp/*
    async def mcp_asgi_app(scope, receive, send):
        """ASGI middleware для MCP endpoints"""
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        
        logger.info(f"📡 MCP ASGI called: {method} {path}")
        
        # Обрабатываем базовый путь /mcp/ или / - информация о сервере
        if (path == "/" or path == "") and method == "GET":
            logger.info("ℹ️ MCP info request")
            import json
            response_data = json.dumps({
                "name": "AmoCRM MCP Server",
                "version": "3.0.0",
                "protocol": "mcp",
                "endpoints": {
                    "sse": "/mcp/sse",
                    "messages": "/mcp/messages"
                },
                "status": "ready"
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": response_data,
            })
        # Обрабатываем SSE endpoint
        elif (path == "/sse" or path == "/mcp/sse" or path.endswith("/sse")) and method == "GET":
            logger.info("🔌 Connecting SSE stream...")
            async with sse_transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await mcp_app.run(
                    read_stream,
                    write_stream,
                    mcp_app.create_initialization_options(),
                )
        # Обрабатываем POST messages
        elif (path == "/messages" or path == "/mcp/messages" or path.endswith("/messages")) and method == "POST":
            logger.info("📨 Handling POST message...")
            await sse_transport.handle_post_message(scope, receive, send)
        else:
            # 404 для неизвестных путей
            logger.warning(f"❌ Unknown MCP path: {method} {path}")
            await send({
                "type": "http.response.start",
                "status": 404,
                "headers": [[b"content-type", b"text/plain"]],
            })
            await send({
                "type": "http.response.body",
                "body": f"Not Found: {path}. Use /mcp/, /mcp/sse or /mcp/messages".encode(),
            })
    
    # Монтируем ASGI приложение
    app.mount("/mcp", mcp_asgi_app)
    
    logger.info("✅ MCP HTTP transport enabled at /mcp/sse and /mcp/messages")
except Exception as _mcp_http_err:
    # Если MCP HTTP транспорт недоступен, просто логируем. REST API продолжит работать.
    logger.error(f"❌ MCP HTTP transport not enabled: {_mcp_http_err}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")

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


@app.get("/api/contacts/search")
async def search_contacts(
    query: str = Query(..., description="Email, телефон или имя для поиска"),
    limit: int = Query(10, description="Количество результатов"),
    authorization: Optional[str] = Header(None)
):
    """
    Поиск контактов по email, телефону или имени.
    Возвращает список найденных контактов с полной информацией.
    """
    try:
        result = await make_amocrm_request(
            "/api/v4/contacts",
            "GET",
            params={"query": query, "limit": limit, "with": "leads"}
        )
        return result
    except Exception as e:
        logger.error(f"Ошибка поиска контактов: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.post("/api/contacts/check-exists")
async def check_contact_exists(
    query: str = Query(..., description="Email или телефон для проверки"),
    authorization: Optional[str] = Header(None)
):
    """
    Проверка существования контакта по email или телефону.
    Возвращает информацию о наличии контакта и его ID если найден.
    """
    try:
        result = await make_amocrm_request(
            "/api/v4/contacts",
            "GET",
            params={"query": query, "limit": 1}
        )
        
        exists = False
        contact_id = None
        contact_data = None
        
        if "_embedded" in result and "contacts" in result["_embedded"]:
            contacts = result["_embedded"]["contacts"]
            if len(contacts) > 0:
                exists = True
                contact_id = contacts[0]["id"]
                contact_data = contacts[0]
        
        return {
            "exists": exists,
            "contact_id": contact_id,
            "contact": contact_data,
            "query": query
        }
    except Exception as e:
        logger.error(f"Ошибка проверки контакта: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.post("/api/contacts/get-or-create")
async def get_or_create_contact(request: Dict[str, Any]):
    """
    Получить контакт если существует, или создать новый.
    Умная операция: сначала ищет по query, если не находит - создает.
    
    Body:
    {
        "query": "email или телефон",
        "name": "Имя контакта",
        "email": "email@example.com",
        "phone": "+79991234567"
    }
    """
    try:
        query = request.get("query")
        if not query:
            return {"error": "Параметр query обязателен", "status": "error"}
        
        # Ищем контакт
        search_result = await make_amocrm_request(
            "/api/v4/contacts",
            "GET",
            params={"query": query, "limit": 1}
        )
        
        if "_embedded" in search_result and "contacts" in search_result["_embedded"]:
            contacts = search_result["_embedded"]["contacts"]
            if len(contacts) > 0:
                return {
                    "found": True,
                    "created": False,
                    "contact": contacts[0]
                }
        
        # Создаем новый контакт
        contact_data = {
            "name": request.get("name", "Новый контакт")
        }
        
        custom_fields = []
        if "email" in request:
            custom_fields.append({
                "field_code": "EMAIL",
                "values": [{"value": request["email"], "enum_code": "WORK"}]
            })
        if "phone" in request:
            custom_fields.append({
                "field_code": "PHONE",
                "values": [{"value": request["phone"], "enum_code": "WORK"}]
            })
        
        if custom_fields:
            contact_data["custom_fields_values"] = custom_fields
        
        create_result = await make_amocrm_request(
            "/api/v4/contacts",
            "POST",
            data=[contact_data]
        )
        
        return {
            "found": False,
            "created": True,
            "contact": create_result
        }
        
    except Exception as e:
        logger.error(f"Ошибка get_or_create_contact: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.post("/api/leads/create-with-contact")
async def create_lead_with_contact(request: Dict[str, Any]):
    """
    Создание сделки с контактом (комплексное создание).
    Если contact_id указан - связывает с существующим контактом.
    Если нет - создает новый контакт вместе со сделкой.
    
    Body:
    {
        "lead_name": "Название сделки",
        "lead_price": 10000,
        "contact_id": 123456,  // опционально, если есть
        "contact_name": "Имя контакта",  // если создаем новый
        "contact_email": "email@example.com",
        "contact_phone": "+79991234567"
    }
    """
    try:
        lead_data = {
            "name": request.get("lead_name", "Новая сделка")
        }
        
        if "lead_price" in request:
            lead_data["price"] = request["lead_price"]
        
        # Если указан ID существующего контакта
        if "contact_id" in request:
            lead_data["_embedded"] = {
                "contacts": [{"id": request["contact_id"]}]
            }
        else:
            # Создаем контакт вместе со сделкой
            contact_data = {
                "name": request.get("contact_name", "Новый контакт")
            }
            
            custom_fields = []
            if "contact_email" in request:
                custom_fields.append({
                    "field_code": "EMAIL",
                    "values": [{"value": request["contact_email"], "enum_code": "WORK"}]
                })
            if "contact_phone" in request:
                custom_fields.append({
                    "field_code": "PHONE",
                    "values": [{"value": request["contact_phone"], "enum_code": "WORK"}]
                })
            
            if custom_fields:
                contact_data["custom_fields_values"] = custom_fields
            
            lead_data["_embedded"] = {
                "contacts": [contact_data]
            }
        
        # Используем complex endpoint для создания
        result = await make_amocrm_request(
            "/api/v4/leads/complex",
            "POST",
            data=[lead_data]
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка создания сделки с контактом: {str(e)}")
        return {"error": str(e), "status": "error"}


@app.post("/api/smart/client-and-lead")
async def smart_create_client_and_lead(request: Dict[str, Any]):
    """
    УМНОЕ создание: полный цикл работы с клиентом и сделкой.
    
    Алгоритм:
    1. Проверяет существование контакта по email/телефону
    2. Если не существует - создает контакт
    3. Проверяет есть ли у контакта открытые сделки
    4. Если нет - создает новую сделку
    
    Body:
    {
        "contact_query": "email или телефон",
        "contact_name": "Имя контакта",
        "contact_email": "email@example.com",
        "contact_phone": "+79991234567",
        "lead_name": "Название сделки",
        "lead_price": 10000,
        "check_existing_leads": true  // проверять ли наличие сделок
    }
    """
    try:
        query = request.get("contact_query")
        if not query:
            return {"error": "Параметр contact_query обязателен", "status": "error"}
        
        steps = []
        
        # Шаг 1: Проверяем контакт
        steps.append("Проверка существования контакта...")
        search_result = await make_amocrm_request(
            "/api/v4/contacts",
            "GET",
            params={"query": query, "limit": 1, "with": "leads"}
        )
        
        contact_id = None
        contact_exists = False
        
        if "_embedded" in search_result and "contacts" in search_result["_embedded"]:
            contacts = search_result["_embedded"]["contacts"]
            if len(contacts) > 0:
                contact_exists = True
                contact_id = contacts[0]["id"]
                steps.append(f"✓ Контакт найден (ID: {contact_id})")
        
        # Шаг 2: Создаем контакт если не существует
        if not contact_exists:
            steps.append("Создание нового контакта...")
            contact_data = {
                "name": request.get("contact_name", "Новый контакт")
            }
            
            custom_fields = []
            if "contact_email" in request:
                custom_fields.append({
                    "field_code": "EMAIL",
                    "values": [{"value": request["contact_email"], "enum_code": "WORK"}]
                })
            if "contact_phone" in request:
                custom_fields.append({
                    "field_code": "PHONE",
                    "values": [{"value": request["contact_phone"], "enum_code": "WORK"}]
                })
            
            if custom_fields:
                contact_data["custom_fields_values"] = custom_fields
            
            create_result = await make_amocrm_request(
                "/api/v4/contacts",
                "POST",
                data=[contact_data]
            )
            
            if "_embedded" in create_result and "contacts" in create_result["_embedded"]:
                contact_id = create_result["_embedded"]["contacts"][0]["id"]
                steps.append(f"✓ Контакт создан (ID: {contact_id})")
        
        # Шаг 3: Проверяем существующие сделки если нужно
        should_create_lead = True
        if request.get("check_existing_leads", True) and contact_id:
            steps.append("Проверка существующих сделок...")
            leads_result = await make_amocrm_request(
                "/api/v4/leads",
                "GET",
                params={
                    "filter[contacts][0]": contact_id,
                    "limit": 1
                }
            )
            
            if "_embedded" in leads_result and "leads" in leads_result["_embedded"]:
                leads = leads_result["_embedded"]["leads"]
                if len(leads) > 0:
                    should_create_lead = False
                    steps.append(f"! У контакта уже есть сделки ({len(leads)} шт.)")
        
        # Шаг 4: Создаем сделку
        lead_result = None
        if should_create_lead and contact_id:
            steps.append("Создание сделки...")
            lead_data = {
                "name": request.get("lead_name", "Новая сделка"),
                "_embedded": {
                    "contacts": [{"id": contact_id}]
                }
            }
            
            if "lead_price" in request:
                lead_data["price"] = request["lead_price"]
            
            lead_result = await make_amocrm_request(
                "/api/v4/leads",
                "POST",
                data=[lead_data]
            )
            
            if "_embedded" in lead_result and "leads" in lead_result["_embedded"]:
                lead_id = lead_result["_embedded"]["leads"][0]["id"]
                steps.append(f"✓ Сделка создана (ID: {lead_id})")
        
        return {
            "success": True,
            "steps": steps,
            "contact_id": contact_id,
            "contact_was_created": not contact_exists,
            "lead_was_created": should_create_lead,
            "lead_result": lead_result
        }
        
    except Exception as e:
        logger.error(f"Ошибка smart_create_client_and_lead: {str(e)}")
        return {"error": str(e), "status": "error", "steps": steps}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

