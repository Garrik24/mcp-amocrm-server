#!/usr/bin/env python3
"""
AmoCRM MCP Server
Сервер Model Context Protocol для работы с AmoCRM API
Поддерживает все основные операции с контактами, сделками, компаниями и задачами
"""

import os
import asyncio
import json
from typing import Any, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
import httpx
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
AMOCRM_SERVER_URL = os.getenv("AMOCRM_SERVER_URL", "http://localhost:8000")
AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN")
AMOCRM_ACCESS_TOKEN = os.getenv("AMOCRM_ACCESS_TOKEN")
AMO_SSL_VERIFY = os.getenv("AMO_SSL_VERIFY", "true").lower() == "true"

# Инициализация MCP сервера
app = Server("amocrm-mcp-server")


async def make_api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[dict] = None,
    params: Optional[dict] = None
) -> dict:
    """Выполняет запрос к локальному FastAPI серверу AmoCRM"""
    url = f"{AMOCRM_SERVER_URL}{endpoint}"
    
    async with httpx.AsyncClient(verify=AMO_SSL_VERIFY, timeout=30.0) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(url)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": str(e), "status": "error"}


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Список всех доступных инструментов MCP"""
    return [
        # ========== КОНТАКТЫ ==========
        Tool(
            name="search_contact",
            description="Поиск контакта по email или телефону в AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Email или телефон для поиска контакта"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_contacts",
            description="Получить список контактов из AmoCRM с возможностью фильтрации",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Количество контактов (по умолчанию 50)",
                        "default": 50
                    },
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос для фильтрации"
                    }
                }
            }
        ),
        Tool(
            name="get_contact_by_id",
            description="Получить контакт по его ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "number",
                        "description": "ID контакта в AmoCRM"
                    }
                },
                "required": ["contact_id"]
            }
        ),
        Tool(
            name="create_contact",
            description="Создать новый контакт в AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Имя контакта"
                    },
                    "first_name": {
                        "type": "string",
                        "description": "Имя"
                    },
                    "last_name": {
                        "type": "string",
                        "description": "Фамилия"
                    },
                    "custom_fields_values": {
                        "type": "array",
                        "description": "Кастомные поля (email, phone и т.д.)",
                        "items": {"type": "object"}
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="update_contact",
            description="Обновить существующий контакт",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "number",
                        "description": "ID контакта"
                    },
                    "data": {
                        "type": "object",
                        "description": "Данные для обновления"
                    }
                },
                "required": ["contact_id", "data"]
            }
        ),
        Tool(
            name="check_contact_exists",
            description="Проверить существует ли контакт по email или телефону",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Email или телефон для проверки"
                    }
                },
                "required": ["query"]
            }
        ),
        
        # ========== СДЕЛКИ ==========
        Tool(
            name="get_leads",
            description="Получить список сделок из AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Количество сделок",
                        "default": 50
                    },
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос"
                    },
                    "status_id": {
                        "type": "number",
                        "description": "ID статуса сделки"
                    },
                    "pipeline_id": {
                        "type": "number",
                        "description": "ID воронки"
                    }
                }
            }
        ),
        Tool(
            name="get_lead_by_id",
            description="Получить сделку по ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "number",
                        "description": "ID сделки"
                    }
                },
                "required": ["lead_id"]
            }
        ),
        Tool(
            name="create_lead",
            description="Создать новую сделку в AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название сделки"
                    },
                    "price": {
                        "type": "number",
                        "description": "Бюджет сделки"
                    },
                    "pipeline_id": {
                        "type": "number",
                        "description": "ID воронки"
                    },
                    "status_id": {
                        "type": "number",
                        "description": "ID статуса"
                    },
                    "responsible_user_id": {
                        "type": "number",
                        "description": "ID ответственного"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="create_complex_lead",
            description="Создать сделку вместе с контактом (комплексное создание)",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_name": {
                        "type": "string",
                        "description": "Название сделки"
                    },
                    "lead_price": {
                        "type": "number",
                        "description": "Бюджет сделки"
                    },
                    "contact_name": {
                        "type": "string",
                        "description": "Имя контакта"
                    },
                    "contact_email": {
                        "type": "string",
                        "description": "Email контакта"
                    },
                    "contact_phone": {
                        "type": "string",
                        "description": "Телефон контакта"
                    }
                },
                "required": ["lead_name", "contact_name"]
            }
        ),
        Tool(
            name="update_lead",
            description="Обновить сделку",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "number",
                        "description": "ID сделки"
                    },
                    "data": {
                        "type": "object",
                        "description": "Данные для обновления"
                    }
                },
                "required": ["lead_id", "data"]
            }
        ),
        Tool(
            name="delete_lead",
            description="Удалить сделку",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "number",
                        "description": "ID сделки для удаления"
                    }
                },
                "required": ["lead_id"]
            }
        ),
        Tool(
            name="get_leads_by_contact",
            description="Получить все сделки конкретного контакта",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "number",
                        "description": "ID контакта"
                    }
                },
                "required": ["contact_id"]
            }
        ),
        
        # ========== КОМПАНИИ ==========
        Tool(
            name="get_companies",
            description="Получить список компаний",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Количество компаний",
                        "default": 50
                    },
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос"
                    }
                }
            }
        ),
        Tool(
            name="create_company",
            description="Создать новую компанию",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название компании"
                    }
                },
                "required": ["name"]
            }
        ),
        
        # ========== ЗАДАЧИ ==========
        Tool(
            name="create_task",
            description="Создать задачу в AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Текст задачи"
                    },
                    "entity_id": {
                        "type": "number",
                        "description": "ID сущности (сделки/контакта)"
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Тип сущности (leads/contacts)",
                        "enum": ["leads", "contacts", "companies"]
                    },
                    "task_type_id": {
                        "type": "number",
                        "description": "Тип задачи (1-Связаться, 2-Встреча)",
                        "default": 1
                    },
                    "complete_till": {
                        "type": "number",
                        "description": "Срок выполнения (Unix timestamp)"
                    }
                },
                "required": ["text", "entity_id", "entity_type"]
            }
        ),
        
        # ========== НАСТРОЙКИ ==========
        Tool(
            name="get_account_info",
            description="Получить информацию об аккаунте AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_pipelines",
            description="Получить список воронок продаж",
            inputSchema={
                "type": "object",
                "properties": {
                    "pipeline_id": {
                        "type": "number",
                        "description": "ID конкретной воронки (опционально)"
                    }
                }
            }
        ),
        Tool(
            name="get_users",
            description="Получить список пользователей аккаунта",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        
        # ========== УМНЫЕ ОПЕРАЦИИ ==========
        Tool(
            name="smart_create_client_and_lead",
            description="Умное создание: проверяет существование контакта, создает если нет, затем создает сделку",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_query": {
                        "type": "string",
                        "description": "Email или телефон для поиска контакта"
                    },
                    "contact_name": {
                        "type": "string",
                        "description": "Имя контакта (если нужно создать)"
                    },
                    "lead_name": {
                        "type": "string",
                        "description": "Название сделки"
                    },
                    "lead_price": {
                        "type": "number",
                        "description": "Бюджет сделки"
                    }
                },
                "required": ["contact_query", "contact_name", "lead_name"]
            }
        ),
        Tool(
            name="get_or_create_contact",
            description="Получить контакт если существует, или создать новый",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Email или телефон"
                    },
                    "name": {
                        "type": "string",
                        "description": "Имя контакта (для создания)"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email (для создания)"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Телефон (для создания)"
                    }
                },
                "required": ["query", "name"]
            }
        ),
        
        # ========== ОТЧЕТЫ ==========
        Tool(
            name="get_deals_report",
            description="Получить отчет по сделкам с фильтрами",
            inputSchema={
                "type": "object",
                "properties": {
                    "created_at_from": {
                        "type": "number",
                        "description": "Дата создания от (Unix timestamp)"
                    },
                    "updated_at_from": {
                        "type": "number",
                        "description": "Дата обновления от (Unix timestamp)"
                    },
                    "status_id": {
                        "type": "number",
                        "description": "ID статуса"
                    },
                    "pipeline_id": {
                        "type": "number",
                        "description": "ID воронки"
                    }
                }
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Обработка вызовов инструментов"""
    
    try:
        # ========== КОНТАКТЫ ==========
        if name == "search_contact":
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "contacts",
                    "method": "get",
                    "params": {"query": arguments["query"], "limit": 10}
                }
            )
            
        elif name == "get_contacts":
            params = {"limit": arguments.get("limit", 50)}
            if "query" in arguments:
                params["query"] = arguments["query"]
            result = await make_api_request(
                "/api/entities",
                "POST",
                {"entity_type": "contacts", "method": "get", "params": params}
            )
            
        elif name == "get_contact_by_id":
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "contacts",
                    "method": "get",
                    "entity_id": arguments["contact_id"]
                }
            )
            
        elif name == "create_contact":
            contact_data = {
                "name": arguments["name"]
            }
            if "first_name" in arguments:
                contact_data["first_name"] = arguments["first_name"]
            if "last_name" in arguments:
                contact_data["last_name"] = arguments["last_name"]
            if "custom_fields_values" in arguments:
                contact_data["custom_fields_values"] = arguments["custom_fields_values"]
                
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "contacts",
                    "method": "post",
                    "data": [contact_data]
                }
            )
            
        elif name == "update_contact":
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "contacts",
                    "method": "patch",
                    "entity_id": arguments["contact_id"],
                    "data": arguments["data"]
                }
            )
            
        elif name == "check_contact_exists":
            search_result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "contacts",
                    "method": "get",
                    "params": {"query": arguments["query"], "limit": 1}
                }
            )
            
            exists = False
            contact_id = None
            if "_embedded" in search_result and "contacts" in search_result["_embedded"]:
                contacts = search_result["_embedded"]["contacts"]
                if len(contacts) > 0:
                    exists = True
                    contact_id = contacts[0]["id"]
            
            result = {
                "exists": exists,
                "contact_id": contact_id,
                "query": arguments["query"]
            }
            
        # ========== СДЕЛКИ ==========
        elif name == "get_leads":
            params = {"limit": arguments.get("limit", 50)}
            if "query" in arguments:
                params["query"] = arguments["query"]
            if "status_id" in arguments:
                params["filter[statuses][0][status_id]"] = arguments["status_id"]
            if "pipeline_id" in arguments:
                params["filter[statuses][0][pipeline_id]"] = arguments["pipeline_id"]
                
            result = await make_api_request(
                "/api/entities",
                "POST",
                {"entity_type": "leads", "method": "get", "params": params}
            )
            
        elif name == "get_lead_by_id":
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "leads",
                    "method": "get",
                    "entity_id": arguments["lead_id"]
                }
            )
            
        elif name == "create_lead":
            lead_data = {
                "name": arguments["name"]
            }
            if "price" in arguments:
                lead_data["price"] = arguments["price"]
            if "pipeline_id" in arguments:
                lead_data["pipeline_id"] = arguments["pipeline_id"]
            if "status_id" in arguments:
                lead_data["status_id"] = arguments["status_id"]
            if "responsible_user_id" in arguments:
                lead_data["responsible_user_id"] = arguments["responsible_user_id"]
                
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "leads",
                    "method": "post",
                    "data": [lead_data]
                }
            )
            
        elif name == "create_complex_lead":
            # Создаем сделку с контактом одновременно
            lead_data = {
                "name": arguments["lead_name"],
                "_embedded": {
                    "contacts": [
                        {"name": arguments["contact_name"]}
                    ]
                }
            }
            
            if "lead_price" in arguments:
                lead_data["price"] = arguments["lead_price"]
                
            # Добавляем кастомные поля контакта если указаны
            custom_fields = []
            if "contact_email" in arguments:
                custom_fields.append({
                    "field_code": "EMAIL",
                    "values": [{"value": arguments["contact_email"], "enum_code": "WORK"}]
                })
            if "contact_phone" in arguments:
                custom_fields.append({
                    "field_code": "PHONE",
                    "values": [{"value": arguments["contact_phone"], "enum_code": "WORK"}]
                })
                
            if custom_fields:
                lead_data["_embedded"]["contacts"][0]["custom_fields_values"] = custom_fields
            
            # Используем комплексный эндпоинт AmoCRM
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "leads/complex",
                    "method": "post",
                    "data": [lead_data]
                }
            )
            
        elif name == "update_lead":
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "leads",
                    "method": "patch",
                    "entity_id": arguments["lead_id"],
                    "data": arguments["data"]
                }
            )
            
        elif name == "delete_lead":
            result = await make_api_request(
                f"/api/entities/leads/{arguments['lead_id']}",
                "DELETE"
            )
            
        elif name == "get_leads_by_contact":
            # Получаем сделки с фильтром по контакту
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "leads",
                    "method": "get",
                    "params": {
                        "filter[contacts][0]": arguments["contact_id"],
                        "with": "contacts"
                    }
                }
            )
            
        # ========== КОМПАНИИ ==========
        elif name == "get_companies":
            params = {"limit": arguments.get("limit", 50)}
            if "query" in arguments:
                params["query"] = arguments["query"]
                
            result = await make_api_request(
                "/api/entities",
                "POST",
                {"entity_type": "companies", "method": "get", "params": params}
            )
            
        elif name == "create_company":
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "companies",
                    "method": "post",
                    "data": [{"name": arguments["name"]}]
                }
            )
            
        # ========== ЗАДАЧИ ==========
        elif name == "create_task":
            import time
            task_data = {
                "text": arguments["text"],
                "entity_id": arguments["entity_id"],
                "entity_type": arguments["entity_type"],
                "task_type_id": arguments.get("task_type_id", 1),
                "complete_till": arguments.get("complete_till", int(time.time()) + 86400)
            }
            
            result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "tasks",
                    "method": "post",
                    "data": [task_data]
                }
            )
            
        # ========== НАСТРОЙКИ ==========
        elif name == "get_account_info":
            result = await make_api_request("/api/account", "GET")
            
        elif name == "get_pipelines":
            if "pipeline_id" in arguments:
                result = await make_api_request(
                    f"/api/pipelines?pipeline_id={arguments['pipeline_id']}",
                    "GET"
                )
            else:
                result = await make_api_request("/api/pipelines", "GET")
                
        elif name == "get_users":
            result = await make_api_request("/api/users", "GET")
            
        # ========== УМНЫЕ ОПЕРАЦИИ ==========
        elif name == "smart_create_client_and_lead":
            # Шаг 1: Проверяем существование контакта
            check_result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "contacts",
                    "method": "get",
                    "params": {"query": arguments["contact_query"], "limit": 1}
                }
            )
            
            contact_id = None
            contact_exists = False
            
            if "_embedded" in check_result and "contacts" in check_result["_embedded"]:
                contacts = check_result["_embedded"]["contacts"]
                if len(contacts) > 0:
                    contact_exists = True
                    contact_id = contacts[0]["id"]
            
            # Шаг 2: Создаем контакт если не существует
            if not contact_exists:
                create_contact_result = await make_api_request(
                    "/api/entities",
                    "POST",
                    {
                        "entity_type": "contacts",
                        "method": "post",
                        "data": [{"name": arguments["contact_name"]}]
                    }
                )
                
                if "_embedded" in create_contact_result and "contacts" in create_contact_result["_embedded"]:
                    contact_id = create_contact_result["_embedded"]["contacts"][0]["id"]
            
            # Шаг 3: Создаем сделку
            if contact_id:
                lead_data = {
                    "name": arguments["lead_name"],
                    "_embedded": {
                        "contacts": [{"id": contact_id}]
                    }
                }
                
                if "lead_price" in arguments:
                    lead_data["price"] = arguments["lead_price"]
                
                lead_result = await make_api_request(
                    "/api/entities",
                    "POST",
                    {
                        "entity_type": "leads",
                        "method": "post",
                        "data": [lead_data]
                    }
                )
                
                result = {
                    "success": True,
                    "contact_id": contact_id,
                    "contact_was_created": not contact_exists,
                    "lead_result": lead_result
                }
            else:
                result = {"success": False, "error": "Не удалось создать контакт"}
                
        elif name == "get_or_create_contact":
            # Сначала ищем
            search_result = await make_api_request(
                "/api/entities",
                "POST",
                {
                    "entity_type": "contacts",
                    "method": "get",
                    "params": {"query": arguments["query"], "limit": 1}
                }
            )
            
            if "_embedded" in search_result and "contacts" in search_result["_embedded"]:
                contacts = search_result["_embedded"]["contacts"]
                if len(contacts) > 0:
                    result = {
                        "found": True,
                        "created": False,
                        "contact": contacts[0]
                    }
                else:
                    # Создаем новый
                    contact_data = {"name": arguments["name"]}
                    custom_fields = []
                    
                    if "email" in arguments:
                        custom_fields.append({
                            "field_code": "EMAIL",
                            "values": [{"value": arguments["email"], "enum_code": "WORK"}]
                        })
                    if "phone" in arguments:
                        custom_fields.append({
                            "field_code": "PHONE",
                            "values": [{"value": arguments["phone"], "enum_code": "WORK"}]
                        })
                    
                    if custom_fields:
                        contact_data["custom_fields_values"] = custom_fields
                    
                    create_result = await make_api_request(
                        "/api/entities",
                        "POST",
                        {
                            "entity_type": "contacts",
                            "method": "post",
                            "data": [contact_data]
                        }
                    )
                    
                    result = {
                        "found": False,
                        "created": True,
                        "contact": create_result
                    }
            else:
                result = search_result
                
        # ========== ОТЧЕТЫ ==========
        elif name == "get_deals_report":
            params = {}
            if "created_at_from" in arguments:
                params["created_at_from"] = arguments["created_at_from"]
            if "updated_at_from" in arguments:
                params["updated_at_from"] = arguments["updated_at_from"]
            if "status_id" in arguments:
                params["status_id"] = arguments["status_id"]
            if "pipeline_id" in arguments:
                params["pipeline_id"] = arguments["pipeline_id"]
                
            result = await make_api_request("/api/report/deals", "GET", params=params)
            
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        # Форматируем результат для MCP
        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "tool": name,
                "arguments": arguments
            }, ensure_ascii=False, indent=2)
        )]


async def main():
    """Запуск MCP сервера"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

