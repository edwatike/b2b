from typing import Dict, Any
from fastapi import Request, Body, HTTPException
from fastapi.routing import APIRouter

router = APIRouter()

@router.post("/search")
async def search(
    request: Request,
    query: str = Body(..., description="Поисковый запрос"),
    limit: int = Body(30, description="Максимальное количество результатов"),
    pages: int = Body(3, description="Количество страниц для поиска"),
    search_engine: str = Body("yandex", description="Поисковая система (yandex или google)"),
    force_update: bool = Body(False, description="Принудительное обновление результатов")
) -> Dict[str, Any]:
    """
    Выполняет поиск по заданному запросу.
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов
        pages: Количество страниц для поиска
        search_engine: Поисковая система (yandex или google)
        force_update: Принудительное обновление результатов
        
    Returns:
        Dict[str, Any]: Результаты поиска
    """
    try:
        parser_service = request.app.state.parser_service
        
        # Сначала получаем результаты поиска
        results = await parser_service.search(
            query=query,
            limit=limit,
            pages=pages,
            engine=search_engine
        )
        
        # Затем сохраняем результаты с учетом force_update
        saved_results = await parser_service.search_and_save(
            keyword=query,
            max_results=limit,
            force_update=force_update
        )
        
        return {
            "results": results,
            "total": len(results),
            "cached": 0 if force_update else len(results),
            "new": len(results) if force_update else 0,
            "search_mode": search_engine
        }
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при выполнении поиска: {str(e)}"
        ) 