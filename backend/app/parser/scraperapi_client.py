import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SCRAPER_API_KEY = "eb97921b1bc73b62af428576f9126bcf"
SCRAPER_API_URL = "http://api.scraperapi.com"

async def scrape_url_with_scraperapi(url: str) -> Optional[str]:
    """
    Отправляет GET-запрос через ScraperAPI и возвращает HTML-код страницы.
    
    Args:
        url: URL страницы для парсинга
        
    Returns:
        str: HTML-код страницы или None в случае ошибки
    """
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
        "render": "true"  # Включаем рендеринг JavaScript
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Отправка запроса к ScraperAPI для URL: {url}")
            response = await client.get(SCRAPER_API_URL, params=params)
            
            if response.status_code == 200:
                logger.info("Успешно получен ответ от ScraperAPI")
                return response.text
            else:
                logger.error(f"Ошибка ScraperAPI. Код статуса: {response.status_code}")
                logger.error(f"Текст ответа: {response.text[:500]}")
                return None
                
    except httpx.TimeoutException:
        logger.error("Таймаут при запросе к ScraperAPI")
        return None
    except httpx.RequestError as e:
        logger.error(f"Ошибка при запросе к ScraperAPI: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        return None 