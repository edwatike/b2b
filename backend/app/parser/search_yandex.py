import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import random
import asyncio
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_random_headers() -> dict:
    user_agent = UserAgent().random
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "DNT": "1",
        "Referer": "https://yandex.ru/",
        "Cookie": f"yandexuid={random.randint(1000000000, 9999999999)}"
    }

YANDEX_SEARCH_URL = "https://yandex.ru/search/"

async def search_yandex(query: str, max_results: int = 10, proxy: Optional[str] = None) -> list[str]:
    params = {
        "text": query,
        "lr": 213,
        "p": random.randint(0, 5)  # Случайная страница
    }

    links = []
    headers = get_random_headers()

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            proxies=proxy,
            headers=headers
        ) as client:
            # Добавляем случайную задержку перед запросом
            await asyncio.sleep(random.uniform(2, 5))
            
            logger.info(f"Searching Yandex for query: {query}")
            response = await client.get(
                YANDEX_SEARCH_URL,
                params=params
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Пробуем разные селекторы для поиска результатов
                selectors = [
                    "div.serp-item a.link",
                    "div.serp-item a.organic__url",
                    "div.serp-item a.link_theme_outer",
                    "div.serp-item a.link_theme_normal"
                ]
                
                for selector in selectors:
                    for tag in soup.select(selector):
                        href = tag.get("href")
                        if href and href.startswith("http") and "yabs.yandex" not in href:
                            links.append(href)
                            logger.info(f"Found link: {href}")
                            if len(links) >= max_results:
                                break
                    if links:
                        break
                        
                if not links:
                    logger.warning("No links found with any selector")
                    
            else:
                logger.error(f"Yandex search failed with status code: {response.status_code}")
                logger.error(f"Response text: {response.text[:500]}")  # Первые 500 символов ответа
                
    except Exception as e:
        logger.error(f"Error during Yandex search: {str(e)}")
        
    logger.info(f"Total results found: {len(links)}")
    return links
