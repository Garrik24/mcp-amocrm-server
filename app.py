from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os

app = FastAPI(title="AmoCRM MCP Server")

class QueryRequest(BaseModel):
    action: str
    parameters: Optional[Dict[str, Any]] = {}

@app.get("/")
def root():
    return {
        "status": "active",
        "service": "AmoCRM MCP Server",
        "version": "1.0.0",
        "endpoints": [
            "/query - Execute AmoCRM queries",
            "/report/daily - Get daily report",
            "/report/weekly - Get weekly report"
        ]
    }

@app.post("/query")
async def query_amocrm(request: QueryRequest):
    """Основной endpoint для запросов к AmoCRM"""
    return {
        "action": request.action,
        "parameters": request.parameters,
        "message": "Endpoint ready for implementation"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
