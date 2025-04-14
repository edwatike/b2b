from typing import List, Set, Dict, Optional, Any
import logging
import random
import asyncio
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from .playwright_runner import PlaywrightRunner
from .config.parser_config import config
from .utils import extract_domain, is_valid_url, clean_url
from .models import SearchResult
from .helpers.human_like_behavior import HumanLikeBehavior
import urllib.parse

logger = logging.getLogger(__name__)

class GoogleSearch:
    """Реализация поиска в Google с обходом защиты от ботов"""
    
    def __init__(self, playwright_runner: PlaywrightRunner):
        """Инициализация поиска Google с инстансом PlaywrightRunner"""
        self.playwright = playwright_runner
        
    async def search(self, query: str, limit: int = 10, region: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Выполняет поиск в Google с имитацией человеческого поведения.
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            region: Регион для поиска (например, 'ru' для России)
        """
        results = []
        page = None
        max_pages = (limit + 9) // 10  # Количество страниц для достижения limit результатов
        
        try:
            # Получаем страницу из пула
            page = await self.playwright.get_page()
            if not page:
                logger.error("Не удалось получить страницу браузера")
                return results

            # Устанавливаем случайный размер окна
            await page.set_viewport_size({
                "width": random.randint(1024, 1920),
                "height": random.randint(768, 1080)
            })

            for page_num in range(max_pages):
                if len(results) >= limit:
                    break

                # Кодируем запрос для URL
                encoded_query = urllib.parse.quote(query)
                start_index = page_num * 10
                search_url = f"https://www.google.com/search?q={encoded_query}&hl={region or 'ru'}&num=10&start={start_index}"
                
                logger.info(f"Выполняем поиск по URL (страница {page_num + 1}): {search_url}")
                
                # Переходим на страницу поиска
                response = await self.playwright.navigate(page, search_url)
                if not response:
                    logger.error(f"Не удалось перейти на страницу поиска {page_num + 1}")
                    continue

                # Ждем загрузки результатов поиска
                await page.wait_for_selector("div#search", timeout=10000)
                
                # Пробуем различные селекторы для поиска результатов
                selectors = [
                    "div.g div.yuRUbf",  # Новый формат Google
                    "div.g",             # Классический формат
                    "div[jscontroller='SC7lYd']",  # Альтернативный формат
                    "div.rc",            # Старый формат
                ]
                
                search_results = []
                for selector in selectors:
                    search_results = await page.query_selector_all(selector)
                    if search_results:
                        logger.info(f"Найдено {len(search_results)} результатов с селектором {selector} на странице {page_num + 1}")
                        break
                
                for result in search_results:
                    if len(results) >= limit:
                        break

                    try:
                        # Пробуем различные селекторы для заголовка
                        title_selectors = ["h3", "h3.LC20lb", "div.vvjwJb"]
                        title = ""
                        for title_selector in title_selectors:
                            title_element = await result.query_selector(title_selector)
                            if title_element:
                                title = await title_element.inner_text()
                                break
                        
                        # Пробуем различные селекторы для URL
                        url = ""
                        link_element = await result.query_selector("a")
                        if link_element:
                            url = await link_element.get_attribute("href")
                        
                        # Пробуем различные селекторы для описания
                        desc_selectors = ["div.VwiC3b", "div.s", "span.st", "div[data-content-feature='1']"]
                        description = ""
                        for desc_selector in desc_selectors:
                            desc_element = await result.query_selector(desc_selector)
                            if desc_element:
                                description = await desc_element.inner_text()
                                break
                        
                        if url and title:
                            logger.info(f"Найден результат: {title}")
                            results.append({
                                "title": title,
                                "url": url,
                                "description": description,
                                "page": page_num + 1
                            })
                            
                    except Exception as e:
                        logger.error(f"Ошибка при извлечении результата: {str(e)}")
                        continue

                # Добавляем случайную задержку между страницами
                if page_num < max_pages - 1:
                    await asyncio.sleep(random.uniform(1.0, 2.0))

            logger.info(f"Всего найдено результатов: {len(results)} на {max_pages} страницах")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            return results
            
        finally:
            if page:
                await self.playwright.release_page(page)
    
    def _parse_search_results_with_soup(self, content: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Извлекает результаты поиска из HTML страницы Google с помощью BeautifulSoup"""
        results = []
        soup = BeautifulSoup(content, 'html.parser')
        
        # Проверяем различные селекторы для поиска результатов
        selectors = [
            'div.tF2Cxc a',         # Основной селектор для современного Google
            'div.yuRUbf > a',       # Альтернативный селектор
            '.g .rc > a',           # Еще один формат
            'div.g div.r a',        # Старый формат
            'a.cz3goc',             # Другой возможный селектор
            'div[jscontroller] a'   # Общий селектор
        ]
        
        position = 1
        
        # Пробуем каждый селектор
        for selector in selectors:
            link_elements = soup.select(selector)
            if not link_elements:
                continue
                
            logger.info(f"BS4: Найдено {len(link_elements)} ссылок с селектором '{selector}'")
            
            for link in link_elements:
                if len(results) >= limit:
                    break
                    
                href = link.get('href')
                if not href or not href.startswith('http'):
                    continue
                
                # Получаем заголовок
                title_element = link.select_one('h3') or link.select_one('.LC20lb')
                title = title_element.get_text().strip() if title_element else ""
                
                # Получаем сниппет
                snippet = ""
                # Ищем родительский div и затем ищем в нем элемент сниппета
                parent_div = link.find_parent('div', class_='g')
                if parent_div:
                    snippet_element = parent_div.select_one('.VwiC3b') or parent_div.select_one('.st')
                    if snippet_element:
                        snippet = snippet_element.get_text().strip()
                
                # Если заголовок не пустой, добавляем результат
                if title:
                    results.append({
                        "url": href,
                        "title": title,
                        "snippet": snippet,
                        "position": position
                    })
                    position += 1
        
        return results
    
    def _is_valid_result(self, url: str) -> bool:
        """Проверяет, является ли URL подходящим результатом поиска"""
        # Игнорируем URL из списка запрещенных доменов
        domain = extract_domain(url)
        if not domain:
            return False
            
        # Игнорируем некоторые домены (соцсети, поисковики, сервисы)
        blacklisted_domains = [
            'google.', 'youtube.', 'facebook.', 'instagram.', 'twitter.', 
            'vk.com', 'ok.ru', 'yandex.', 'mail.ru', 'rambler.ru'
        ]
        
        for blacklisted in blacklisted_domains:
            if blacklisted in domain:
                return False
                
        return is_valid_url(url) 