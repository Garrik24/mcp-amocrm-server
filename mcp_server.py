#!/usr/bin/env python3
"""
MCP Server для интеграции с AmoCRM через HTTP сервер
"""

import json
import sys
import os
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Any, Dict, List
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# URL вашего AmoCRM сервера
# Берём из переменной окружения AMOCRM_SERVER_URL, иначе localhost
AMOCRM_SERVER_URL = os.getenv("AMOCRM_SERVER_URL", "http://127.0.0.1:8000")

# Создаем MCP сервер
server = Server("amocrm-mcp-server")

def _to_unix(ts_value) -> int:
    """Преобразует ISO-дату/строку/число в Unix timestamp (секунды).
    Допускает значения вида '2025-09-15', '2025-09-15T12:00:00', int/str unix.
    """
    if ts_value is None:
        return None
    # Число/строка числа
    if isinstance(ts_value, (int, float)):
        return int(ts_value)
    s = str(ts_value).strip()
    if s.isdigit():
        return int(s)
    # ISO без времени
    try:
        if len(s) == 10 and s[4] == '-' and s[7] == '-':
            dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
    except Exception:
        pass
    # ISO с временем
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        raise ValueError(f"Неверный формат даты/времени: {ts_value}")

async def make_request(method: str, endpoint: str, data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Выполняет HTTP запрос к AmoCRM серверу"""
    url = f"{AMOCRM_SERVER_URL}{endpoint}"
    
    # Позволяем отключить проверку SSL (например, при нестабильных сертификатах)
    verify_ssl = os.getenv("AMO_SSL_VERIFY", "true").lower() not in {"0", "false", "no"}
    connector = aiohttp.TCPConnector(ssl=False) if not verify_ssl else None
    async with aiohttp.ClientSession(connector=connector) as session:
        if method.upper() == "GET":
            async with session.get(url, params=params) as response:
                return await response.json()
        elif method.upper() == "POST":
            async with session.post(url, json=data) as response:
                return await response.json()

@server.list_resources()
async def handle_list_resources() -> List[types.Resource]:
    """Возвращает список доступных ресурсов AmoCRM"""
    return [
        types.Resource(
            uri="amocrm://status",
            name="AmoCRM Server Status",
            description="Статус AmoCRM сервера",
            mimeType="application/json",
        ),
        types.Resource(
            uri="amocrm://account",
            name="AmoCRM Account Info",
            description="Информация об аккаунте AmoCRM",
            mimeType="application/json",
        ),
        types.Resource(
            uri="amocrm://leads",
            name="AmoCRM Leads",
            description="Сделки в AmoCRM",
            mimeType="application/json",
        ),
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Читает ресурс по URI"""
    if uri == "amocrm://status":
        result = await make_request("GET", "/")
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    elif uri == "amocrm://account":
        result = await make_request("GET", "/api/account")
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    elif uri == "amocrm://leads":
        data = {
            "entity_type": "leads",
            "method": "get",
            "params": {"limit": 10}
        }
        result = await make_request("POST", "/api/entities", data)
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    else:
        raise ValueError(f"Unknown resource: {uri}")

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """Возвращает список доступных инструментов"""
    return [
        types.Tool(
            name="get_amocrm_status",
            description="Получить статус AmoCRM сервера",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_leads",
            description="Получить список сделок из AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Количество сделок для получения",
                        "default": 10
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="create_lead",
            description="Создать новую сделку в AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Название сделки"},
                    "price": {"type": "integer", "description": "Бюджет сделки", "default": 0},
                    "pipeline_id": {"type": "integer", "description": "ID воронки (если не указан, возьмём из переменной окружения AMO_PIPELINE_ID, если задана)"},
                    "status_id": {"type": "integer", "description": "ID статуса этапа (если не указан, возьмём из AMO_STATUS_ID)"},
                    "responsible_user_id": {"type": "integer", "description": "ID ответственного (если не указан, возьмём из AMO_RESPONSIBLE_ID)"}
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="delete_lead",
            description="Удалить сделку по ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {"type": "integer", "description": "ID сделки"}
                },
                "required": ["entity_id"],
            },
        ),
        types.Tool(
            name="amocrm_request",
            description="Универсальный HTTP запрос к AmoCRM серверу. Позволяет вызвать любой endpoint нашего бэкенда.",
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET","POST","PATCH","DELETE"], "description": "HTTP метод"},
                    "path": {"type": "string", "description": "Путь, например: /api/entities"},
                    "params": {"type": "object", "description": "Query-параметры"},
                    "body": {"type": "object", "description": "JSON тело запроса"}
                },
                "required": ["method", "path"],
            },
        ),
        types.Tool(
            name="get_leads_by_date",
            description="Получить сделки за период с фильтрами (удобный алиас)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date_from": {"description": "Начало периода (ISO или unix)"},
                    "date_to": {"description": "Конец периода (ISO или unix)", "nullable": True},
                    "limit": {"type": "integer", "default": 50},
                    "pipeline_id": {"type": "integer"},
                    "status_id": {"type": "integer"}
                },
                "required": ["date_from"],
            },
        ),
        types.Tool(
            name="create_simple_lead",
            description="Быстро создать сделку (алиас). Берёт дефолты из окружения при отсутствии параметров",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "integer", "default": 0},
                    "pipeline_id": {"type": "integer"},
                    "status_id": {"type": "integer"},
                    "responsible_user_id": {"type": "integer"}
                },
                "required": ["name"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Выполняет вызов инструмента"""
    
    if name == "get_amocrm_status":
        result = await make_request("GET", "/")
        return [
            types.TextContent(
                type="text",
                text=f"Статус AmoCRM сервера:\n{json.dumps(result, ensure_ascii=False, indent=2)}"
            )
        ]
    
    elif name == "get_leads":
        limit = arguments.get("limit", 10)
        data = {
            "entity_type": "leads",
            "method": "get",
            "params": {"limit": limit}
        }
        result = await make_request("POST", "/api/entities", data)
        return [
            types.TextContent(
                type="text",
                text=f"Сделки AmoCRM (лимит: {limit}):\n{json.dumps(result, ensure_ascii=False, indent=2)}"
            )
        ]
    
    elif name == "create_lead":
        name_lead = arguments.get("name")
        price = arguments.get("price", 0)
        # Значения по умолчанию из окружения
        pipeline_id = arguments.get("pipeline_id") or (int(os.getenv("AMO_PIPELINE_ID")) if os.getenv("AMO_PIPELINE_ID") else None)
        status_id = arguments.get("status_id") or (int(os.getenv("AMO_STATUS_ID")) if os.getenv("AMO_STATUS_ID") else None)
        responsible_user_id = arguments.get("responsible_user_id") or (int(os.getenv("AMO_RESPONSIBLE_ID")) if os.getenv("AMO_RESPONSIBLE_ID") else None)

        lead: Dict[str, Any] = {"name": name_lead, "price": price}
        if pipeline_id is not None:
            lead["pipeline_id"] = pipeline_id
        if status_id is not None:
            lead["status_id"] = status_id
        if responsible_user_id is not None:
            lead["responsible_user_id"] = responsible_user_id

        data = {
            "entity_type": "leads",
            "method": "post",
            "data": [lead]
        }
        result = await make_request("POST", "/api/entities", data)
        return [
            types.TextContent(
                type="text",
                text=f"Создана сделка '{name_lead}':\n{json.dumps(result, ensure_ascii=False, indent=2)}"
            )
        ]
    
    elif name == "delete_lead":
        entity_id = arguments.get("entity_id")
        if entity_id is None:
            raise ValueError("entity_id is required")
        # Вызываем POST-обёртку удаления, чтобы избежать ограничений на методы в некоторых клиентах
        result = await make_request("POST", f"/api/entities/leads/{int(entity_id)}/delete")
        return [
            types.TextContent(
                type="text",
                text=f"Удаление сделки {entity_id}:\n{json.dumps(result, ensure_ascii=False, indent=2)}"
            )
        ]
    
    elif name == "amocrm_request":
        method = str(arguments.get("method", "GET")).upper()
        path = arguments.get("path")
        if not path or not path.startswith("/"):
            raise ValueError("'path' must start with '/'")
        params = arguments.get("params")
        body = arguments.get("body")
        if method in {"GET","DELETE"}:
            result = await make_request(method, path, params=params)
        else:
            result = await make_request(method, path, body)
        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )
        ]

    elif name == "get_leads_by_date":
        date_from = _to_unix(arguments.get("date_from"))
        date_to = _to_unix(arguments.get("date_to")) if arguments.get("date_to") is not None else None
        limit = int(arguments.get("limit", 50))
        pipeline_id = arguments.get("pipeline_id")
        status_id = arguments.get("status_id")

        # Формируем параметры для отчёта
        query_params = {"created_at_from": date_from, "limit": limit}
        if date_to is not None:
            query_params["created_at_to"] = date_to
        if pipeline_id is not None:
            query_params["pipeline_id"] = int(pipeline_id)
        if status_id is not None:
            query_params["status_id"] = int(status_id)

        # Используем удобный отчётный эндпоинт бэкенда
        # Для простоты передаём как GET-путь с querystring
        qs = "&".join(f"{k}={v}" for k, v in query_params.items() if v is not None)
        path = f"/api/report/deals?{qs}"
        result = await make_request("GET", path)
        return [
            types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))
        ]

    elif name == "create_simple_lead":
        name_lead = arguments.get("name")
        price = int(arguments.get("price", 0))
        pipeline_id = arguments.get("pipeline_id") or (int(os.getenv("AMO_PIPELINE_ID")) if os.getenv("AMO_PIPELINE_ID") else None)
        status_id = arguments.get("status_id") or (int(os.getenv("AMO_STATUS_ID")) if os.getenv("AMO_STATUS_ID") else None)
        responsible_user_id = arguments.get("responsible_user_id") or (int(os.getenv("AMO_RESPONSIBLE_ID")) if os.getenv("AMO_RESPONSIBLE_ID") else None)

        lead: Dict[str, Any] = {"name": name_lead, "price": price}
        if pipeline_id is not None:
            lead["pipeline_id"] = pipeline_id
        if status_id is not None:
            lead["status_id"] = status_id
        if responsible_user_id is not None:
            lead["responsible_user_id"] = responsible_user_id

        body = {"entity_type": "leads", "method": "post", "data": [lead]}
        result = await make_request("POST", "/api/entities", body)
        return [
            types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))
        ]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Запуск MCP сервера через stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="amocrm-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
