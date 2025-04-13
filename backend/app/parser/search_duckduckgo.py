import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import random
import asyncio
import logging
from typing import Optional
from urllib.parse import quote, unquote

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
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "DNT": "1"
    }

DUCKDUCKGO_SEARCH_URL = "https://html.duckduckgo.com/html/"

async def search_duckduckgo(query: str, max_results: int = 10) -> list[str]:
    params = {
        "q": f"{query} site:.ru",  # Ограничиваем поиск русскоязычными сайтами
        "kl": "ru-ru",  # Русская локаль
        "s": "0"  # Начальная позиция
    }

    links = []
    headers = get_random_headers()

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers=headers
        ) as client:
            # Добавляем небольшую случайную задержку
            await asyncio.sleep(random.uniform(1, 2))
            
            logger.info(f"Searching DuckDuckGo for query: {query}")
            response = await client.post(
                DUCKDUCKGO_SEARCH_URL,
                data=params
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Сохраняем HTML для отладки
                logger.debug(f"Response HTML: {response.text}")
                
                # Ищем все результаты поиска
                for result in soup.select(".links_main"):
                    link_element = result.select_one("a.result__url")
                    if not link_element:
                        link_element = result.select_one("a.result__a")
                    
                    if link_element:
                        href = link_element.get("href")
                        if not href:
                            continue
                            
                        # Очищаем URL от редиректов DuckDuckGo
                        if "/d.js?" in href:
                            href = unquote(href.split("uddg=")[-1].split("&rut=")[0])
                            
                        if href and href.startswith("http"):
                            links.append(href)
                            logger.info(f"Found link: {href}")
                            if len(links) >= max_results:
                                break
                                
                if not links:
                    logger.warning("No links found in the search results")
                    logger.debug("Available elements:")
                    for element in soup.select("a"):
                        logger.debug(f"Element: {element}")
                    
            else:
                logger.error(f"DuckDuckGo search failed with status code: {response.status_code}")
                logger.error(f"Response text: {response.text[:500]}")  # Первые 500 символов ответа
                
    except Exception as e:
        logger.error(f"Error during DuckDuckGo search: {str(e)}")
        
    logger.info(f"Total results found: {len(links)}")
    return links 