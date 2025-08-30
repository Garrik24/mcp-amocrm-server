import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import aiohttp

# Настройки AmoCRM
AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN", "stavgeo26")
AMOCRM_ACCESS_TOKEN = os.getenv("AMOCRM_ACCESS_TOKEN")

server = Server("amocrm-mcp")

async def make_amocrm_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> Dict[str, Any]:
    """Выполнить запрос к AmoCRM API"""
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru{endpoint}"
    headers = {
        "Authorization": f"Bearer {AMOCRM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url, headers=headers, params=params) as response:
                return await response.json()
        elif method == "POST":
            async with session.post(url, headers=headers, json=data) as response:
                return await response.json()

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """Список доступных инструментов"""
    return [
        types.Tool(
            name="get_leads",
            description="Получить список сделок из AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Количество сделок",
                        "default": 10
                    }
                }
            }
        ),
        types.Tool(
            name="get_contacts",
            description="Получить список контактов из AmoCRM",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Количество контактов",
                        "default": 10
                    }
                }
            }
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
                        "description": "Сумма сделки"
                    }
                },
                "required": ["name"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: Optional[Dict[str, Any]] = None
) -> List[types.TextContent]:
    """Обработка вызовов инструментов"""
    
    if name == "get_leads":
        limit = arguments.get("limit", 10) if arguments else 10
        result = await make_amocrm_request(
            "GET", 
            "/api/v4/leads",
            params={"limit": limit}
        )
        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
    
    elif name == "get_contacts":
        limit = arguments.get("limit", 10) if arguments else 10
        result = await make_amocrm_request(
            "GET",
            "/api/v4/contacts", 
            params={"limit": limit}
        )
        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
    
    elif name == "create_lead":
        data = [{
            "name": arguments.get("name"),
            "price": arguments.get("price", 0)
        }]
        result = await make_amocrm_request(
            "POST",
            "/api/v4/leads",
            data=data
        )
        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
    
    else:
        raise ValueError(f"Неизвестный инструмент: {name}")

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="amocrm-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
