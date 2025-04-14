from fastapi import APIRouter, HTTPException
import logging
from typing import Dict, Any, List
import traceback
import asyncio
import json

from app.parser.models import SearchRequest, SearchResponse
from app.parser.parser_service import search_and_save
from app.parser.search_scraperapi import search_scraperapi

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/search")
async def search(request: SearchRequest) -> Dict[str, Any]:
    logger.info(f"✨ Получен запрос на поиск: {request.query}")
    try:
        logger.info(f"⏳ Запускаем поиск для запроса '{request.query}'...")
        
        # Запускаем поиск с подробным логированием
        results = await search_and_save(request.query)
        
        logger.info(f"✅ Поиск завершен! Найдено результатов: {len(results)}")
        
        # Для отладки выводим первые 3 результата
        for i, result in enumerate(results[:3]):
            logger.info(f"  📌 Результат #{i+1}: {json.dumps(result, ensure_ascii=False)}")
            
        # Формируем ответ API
        total_results = len(results)
        response = {
            "results": results,
            "total": total_results,
            "cached": 0,
            "new": total_results
        }
        
        logger.info(f"✉️ Отправляем ответ пользователю: {len(results)} результатов")
        return response
        
    except Exception as e:
        error_detail = f"❌ Ошибка при обработке запроса: {str(e)}"
        logger.error(error_detail)
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Возвращаем пустой результат при ошибке вместо исключения для отладки
        return {
            "results": [],
            "total": 0,
            "cached": 0,
            "new": 0,
            "error": str(e)
        } 