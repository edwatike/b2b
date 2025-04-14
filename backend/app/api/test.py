from fastapi import APIRouter, HTTPException
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test", tags=["test"])

@router.get("/")
async def test_endpoint():
    """Простой эндпоинт для проверки работоспособности API."""
    return {"status": "ok", "message": "API работает!"}

@router.post("/search")
async def test_search(query: str = "шпунт ларсена"):
    """
    Тестовый эндпоинт для поиска с фиксированными результатами.
    Этот эндпоинт не выполняет реальный поиск, а возвращает предопределенные результаты.
    """
    try:
        logger.info(f"Получен тестовый запрос на поиск: {query}")
        
        # Фиксированные результаты для тестирования
        mock_results = [
            {
                "url": "https://ru.wikipedia.org/wiki/Шпунт_Ларсена",
                "title": "Шпунт Ларсена — Википедия",
                "snippet": "Шпунт Ларсена — тип шпунтовой сваи, представляющий собой металлический профиль в виде желоба с замками на обоих краях...",
                "position": 1,
                "source": "google"
            },
            {
                "url": "https://arbaum.ru/vse-o-shpunte/chto-takoe-shpunt-larsena/",
                "title": "Шпунт Ларсена: что это и для чего применяется",
                "snippet": "Шпунт Ларсена представляет собой металлический профиль в виде желоба с замками на обоих краях. Эти замки позволяют...",
                "position": 2,
                "source": "google"
            },
            {
                "url": "http://ustanovkasvai.ru/stati/61-shpunt-larsena",
                "title": "Шпунт Ларсена",
                "snippet": "Этот строительный материал представляет собой стальной профиль особой формы, который соединяется с другими...",
                "position": 3,
                "source": "google"
            }
        ]
        
        logger.info(f"Возвращаем {len(mock_results)} тестовых результатов")
        return {
            "results": mock_results,
            "total": len(mock_results),
            "cached": 0,
            "new": len(mock_results)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении тестового поиска: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}") 