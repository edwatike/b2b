from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from .database import init_db
from .api.parser import router as parser_router
from .parser.main import router as test_router
from .parser.playwright_runner import PlaywrightRunner
from .parser.search_google import GoogleSearch
from .api.test import router as simple_test_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="B2B Parser API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(parser_router)
app.include_router(test_router)
app.include_router(simple_test_router)

# Тестовый маршрут для отладки
@app.get("/test")
async def test_route():
    """Простой тестовый маршрут."""
    return {"message": "API работает!"}

# Глобальные переменные для тестового поиска
playwright_runner = None
google_search = None

@app.get("/test-google")
async def test_google():
    """Тестовый маршрут для поиска в Google."""
    global playwright_runner, google_search
    
    try:
        # Инициализируем Playwright и Google Search, если они еще не инициализированы
        if not playwright_runner:
            logger.info("Инициализация Playwright runner...")
            playwright_runner = PlaywrightRunner()
            await playwright_runner.initialize()
            logger.info("Инициализация Google Search...")
            google_search = GoogleSearch(playwright_runner)
            logger.info("✅ Тестовый поиск инициализирован")
        
        # Выполняем поиск
        logger.info("Выполняем поиск 'шпунт ларсена'...")
        results = await google_search.search("шпунт ларсена", limit=2)
        
        # Форматируем результаты
        formatted_results = []
        for result in results:
            formatted_results.append({
                "url": result.url,
                "title": result.title,
                "snippet": result.snippet,
                "position": result.position
            })
            
        logger.info(f"Найдено результатов: {len(formatted_results)}")
        return {"results": formatted_results}
        
    except Exception as e:
        logger.error(f"Ошибка при тестовом поиске: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@app.on_event("startup")
async def startup_event():
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных инициализирована")
