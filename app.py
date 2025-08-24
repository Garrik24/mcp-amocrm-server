from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
import json
from typing import Dict, List, Optional
import os

app = FastAPI(title="MCP amoCRM Server")

# Получаем ключ из переменных окружения
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Ваш прайс-лист работ
PRICE_LIST = [
    "Межевание участка",
    "Кадастровые работы", 
    "Топографическая съемка",
    "Вынос границ участка",
    "Геодезические работы",
    "Технический план",
    "Акт обследования",
    "Схема расположения",
    "Проект межевания",
    "Градостроительный план"
]

class TranscriptionRequest(BaseModel):
    phone_number: str
    transcription_text: str
    call_duration: int
    call_id: Optional[str] = None

def extract_amounts(text: str) -> List[float]:
    """Извлечение сумм из текста"""
    amounts = []
    
    # Паттерны для поиска сумм
    patterns = [
        (r'(\d+)\s*тысяч', 1000),
        (r'(\d+)\s*тыс', 1000),
        (r'(\d+)к\b', 1000),
        (r'(\d+)\s*руб', 1),
        (r'(\d+)\s*рублей', 1),
    ]
    
    for pattern, multiplier in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            number = float(match.group(1))
            amounts.append(number * multiplier)
    
    return amounts

def find_work_type(text: str) -> str:
    """Поиск вида работ из прайс-листа"""
    text_lower = text.lower()
    for work in PRICE_LIST:
        if work.lower() in text_lower or any(word in text_lower for word in work.lower().split()):
            return work
    return "Консультация"

def extract_location(text: str) -> str:
    """Извлечение местоположения"""
    patterns = [
        r'в\s+([А-Я][а-я]+(?:\s+[А-Я][а-я]+)*)',
        r'город\s+([А-Я][а-я]+)',
        r'на\s+улице\s+([^,\.]+)',
        r'по\s+адресу\s+([^,\.]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return "Не указано"

def extract_next_steps(text: str) -> str:
    """Извлечение следующих шагов"""
    keywords = [
        "позвоню", "позвонить", "перезвоню",
        "отправлю", "отправить", "вышлю", "выслать",
        "встретимся", "встреча", "приедем",
        "подготовлю", "подготовить",
        "презентация", "предложение", "договор"
    ]
    
    text_lower = text.lower()
    for keyword in keywords:
        if keyword in text_lower:
            # Находим предложение с ключевым словом
            sentences = text.split('.')
            for sentence in sentences:
                if keyword in sentence.lower():
                    return sentence.strip()
    
    return "Ожидание решения клиента"

@app.post("/webhook/transcription")
async def process_transcription(request: TranscriptionRequest):
    """Обработка расшифровки звонка"""
    try:
        text = request.transcription_text
        
        # Извлекаем данные
        amounts = extract_amounts(text)
        contract_sum = sum(amounts) if amounts else 0
        work_type = find_work_type(text)
        location = extract_location(text)
        next_steps = extract_next_steps(text)
        
        # Формируем ответ
        extracted_data = {
            "contract_sum": contract_sum,
            "amounts_mentioned": amounts,
            "work_type": work_type,
            "location": location,
            "next_steps": next_steps
        }
        
        return {
            "call_id": request.call_id or "generated",
            "phone_number": request.phone_number,
            "extracted_data": extracted_data,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "MCP amoCRM Server работает!", "status": "active"}

@app.get("/health")
async def health():
    return {"status": "healthy", "api_key_set": bool(ANTHROPIC_API_KEY)}

# Для отладки
@app.post("/test")
async def test_extraction(text: str):
    """Тестовый endpoint для проверки извлечения"""
    return {
        "amounts": extract_amounts(text),
        "work_type": find_work_type(text),
        "location": extract_location(text),
        "next_steps": extract_next_steps(text)
    }

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
