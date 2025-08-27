from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import aiohttp
import json

app = FastAPI(title="AmoCRM MCP Server")

AMOCRM_CLIENT_ID = os.getenv("AMOCRM_CLIENT_ID", "fa0b0e51-e31d-4bdc-834b-b5970e960ce3")
AMOCRM_CLIENT_SECRET = os.getenv("AMOCRM_CLIENT_SECRET", "IPDQVlRfkPvlAls2gSWbKiYxur1QdJZvDSHCjH5F3eNZ3A3KC5af6MTYfGm27khL")
AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN", "stavgeo26")

class QueryRequest(BaseModel):
    action: str
    parameters: Optional[Dict[str, Any]] = {}

@app.get("/")
def root():
    return {
        "status": "active",
        "service": "AmoCRM MCP Server",
        "version": "1.0.0",
        "subdomain": AMOCRM_SUBDOMAIN
    }

@app.post("/auth/get-token")
async def get_token(auth_code: str):
    """Получение токенов по коду авторизации"""
    url = f"https://{AMOCRM_SUBDOMAIN}.amocrm.ru/oauth2/access_token"
    
    data = {
        "client_id": AMOCRM_CLIENT_ID,
        "client_secret": AMOCRM_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": "https://mcp-amocrm-server-production.up.railway.app/callback"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            result = await response.json()
            return {
                "status": response.status,
                "data": result
            }
