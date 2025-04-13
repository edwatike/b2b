from fastapi import APIRouter
from pydantic import BaseModel
from app.parser.main import parse_all_sources
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class SearchQuery(BaseModel):
    query: str

@router.post("/search")
async def run_parser(request: SearchQuery):
    logger.info(f"Получен запрос на поиск: {request.query}")
    results = await parse_all_sources(request.query)
    logger.info(f"Всего найдено уникальных результатов: {len(results)}")
    return {"results": results} 