#!/usr/bin/env python3
"""
MCP Server для интеграции с AmoCRM через HTTP сервер
"""

import json
import sys
import asyncio
import aiohttp
from typing import Any, Dict, List
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# URL вашего AmoCRM сервера
AMOCRM_SERVER_URL = "http://127.0.0.1:8000"

# Создаем MCP сервер
server = Server("amocrm-mcp-server")

async def make_request(method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Выполняет HTTP запрос к AmoCRM серверу"""
    url = f"{AMOCRM_SERVER_URL}{endpoint}"
    
    async with aiohttp.ClientSession() as session:
        if method.upper() == "GET":
            async with session.get(url) as response:
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
                    "name": {
                        "type": "string",
                        "description": "Название сделки"
                    },
                    "price": {
                        "type": "integer",
                        "description": "Бюджет сделки"
                    }
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
        
        data = {
            "entity_type": "leads",
            "method": "post",
            "data": [
                {
                    "name": name_lead,
                    "price": price
                }
            ]
        }
        result = await make_request("POST", "/api/entities", data)
        return [
            types.TextContent(
                type="text",
                text=f"Создана сделка '{name_lead}':\n{json.dumps(result, ensure_ascii=False, indent=2)}"
            )
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
