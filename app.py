from fastapi import FastAPI, HTTPException
import os
from pydantic import BaseModel
from typing import Optional, List
import re

# Создание приложения FastAPI
app = FastAPI(title="MCP amoCRM Server", version="1.0.0")

# Получение API ключа из переменных окружения
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

class TranscriptionRequest(BaseModel):
    call_id: Optional[str] = None
    phone_number: str
    transcription_text: str

def extract_amounts(text: str) -> List[float]:
    """Извлечение сумм из текста"""
    patterns = [
        r'(\d+(?:[\s,]\d{3})*(?:\.\d{2})?)\s*(?:руб|рублей|₽)',
        r'(\d+(?:[\s,]\d{3})*)\s*(?:тысяч|тыс)',
        r'(\d+(?:[\s,]\d{3})*)\s*(?:миллионов?|млн)',
        r'(\d+(?:\.\d+)?)\s*(?:миллионов?|млн)',
        r'(\d+(?:\.\d+)?)\s*(?:тысяч|тыс)'
    ]
    
    amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Очищаем от пробелов и запятых
            clean_match = match.replace(' ', '').replace(',', '')
            try:
                amount = float(clean_match)
                # Конвертируем тысячи и миллионы
                if 'тысяч' in text.lower() or 'тыс' in text.lower():
                    amount *= 1000
                elif 'миллион' in text.lower() or 'млн' in text.lower():
                    amount *= 1000000
                amounts.append(amount)
            except ValueError:
                continue
    
    return amounts

def find_work_type(text: str) -> str:
    """Определение типа работ"""
    work_types = {
        'ремонт': ['ремонт', 'отремонтировать', 'починить'],
        'строительство': ['строительство', 'построить', 'стройка'],
        'отделка': ['отделка', 'отделать', 'покраска', 'поклейка'],
        'сантехника': ['сантехника', 'сантехнические', 'водопровод', 'канализация'],
        'электрика': ['электрика', 'электрические', 'проводка', 'розетки'],
        'дизайн': ['дизайн', 'дизайнерские', 'интерьер']
    }
    
    text_lower = text.lower()
    for work_type, keywords in work_types.items():
        for keyword in keywords:
            if keyword in text_lower:
                return work_type
    
    return "не определен"

def extract_location(text: str) -> str:
    """Извлечение адреса/локации"""
    location_patterns = [
        r'(?:по адресу|адрес)\s*:?\s*([^,.!?\n]+)',
        r'(?:улица|ул\.)\s*([^,.!?\n]+)',
        r'(?:район|р-н)\s*([^,.!?\n]+)',
        r'(?:город|г\.)\s*([^,.!?\n]+)'
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "не указан"

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
