from typing import List, Set, Dict, Optional
import logging
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from .playwright_runner import PlaywrightRunner
from .config.parser_config import config
from .utils import extract_domain, is_valid_url, clean_url
import asyncio
import random

logger = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self, playwright_runner: PlaywrightRunner):
        self.playwright = playwright_runner
        
    async def search(self, query: str, region: Optional[str] = None) -> Set[str]:
        """Perform search and extract unique URLs."""
        unique_urls: Set[str] = set()
        
        try:
            # Get page from pool
            page = await self.playwright.get_page()
            
            try:
                logger.info(f"Начинаем поиск по запросу: '{query}' с регионом '{region or 'не указан'}'")
                
                for page_num in range(config.search_depth):
                    # For first page, we need to navigate to the search engine and type the query
                    if page_num == 0:
                        # Используем Google
                        search_url = "https://www.google.ru"
                        
                        # Начинаем с небольшой случайной задержки
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                        
                        logger.info(f"Переходим на начальную страницу поиска: {search_url}")
                        content = await self.playwright.navigate(page, search_url)
                        
                        if not content:
                            logger.warning("Не удалось загрузить домашнюю страницу поиска")
                            break
                            
                        # Делаем паузу для изучения страницы
                        await asyncio.sleep(random.uniform(1.0, 2.0))
                        
                        # Добавляем случайное действие - иногда проверяем что-то на странице
                        if random.random() < 0.2:
                            # Находим случайный элемент на странице и взаимодействуем с ним
                            elements = await page.query_selector_all("a, button, img")
                            if elements:
                                random_element = random.choice(elements)
                                try:
                                    # Наводим мышь на элемент
                                    await random_element.hover()
                                    await asyncio.sleep(random.uniform(0.5, 1.5))
                                except Exception as e:
                                    logger.debug(f"Незначительная ошибка при взаимодействии с элементом: {e}")
                        
                        # Имитируем человеческий ввод поискового запроса
                        full_query = f"{query} {region if region else ''}"
                        logger.info(f"Вводим поисковый запрос: '{full_query}'")
                        await self.playwright.type_search_query(page, full_query, "textarea[name='q']")
                        
                        # Ждем загрузки результатов с небольшой задержкой
                        await page.wait_for_load_state("networkidle", timeout=config.browser_timeout * 1000)
                        
                        # После загрузки результатов делаем небольшую паузу для "осмотра"
                        await asyncio.sleep(random.uniform(1.5, 3.0))
                        
                    else:
                        # Добавляем естественную задержку между страницами
                        await asyncio.sleep(random.uniform(3.0, 6.0))
                        
                        logger.info(f"Переходим на страницу {page_num + 1} результатов поиска")
                        
                        # Для Google используем страницу результатов с параметром start
                        try:
                            # Создаем URL с элементами случайности (как это делает реальный браузер)
                            params = {
                                "q": query,
                                "start": page_num * 10,
                                "hl": random.choice(["ru", "ru-RU"]),
                                "gl": "ru",
                                "ie": "UTF-8",
                                "oe": "UTF-8",
                                # Добавляем случайный параметр для уникальности запроса
                                "ei": f"{random.randint(10000000, 99999999)}",
                                "ved": f"{''.join(random.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for _ in range(20))}"
                            }
                            
                            # Выбираем случайно - использовать ли элемент навигации или прямой URL
                            if random.random() < 0.6:
                                # Находим кнопку "Следующая" и кликаем на нее
                                next_button_selectors = [
                                    "a#pnnext", 
                                    "a.pn", 
                                    "a[aria-label='Next page']", 
                                    "a[aria-label='Следующая']"
                                ]
                                
                                found_next = False
                                for selector in next_button_selectors:
                                    next_button = await page.query_selector(selector)
                                    if next_button:
                                        # Прокручиваем страницу к кнопке "Следующая"
                                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight - 300)")
                                        await asyncio.sleep(random.uniform(0.5, 1.5))
                                        
                                        # Имитируем естественное движение мыши к кнопке
                                        box = await next_button.bounding_box()
                                        if box:
                                            await self.playwright.human_behavior.human_mouse_move(
                                                page,
                                                box["x"] + box["width"] / 2,
                                                box["y"] + box["height"] / 2
                                            )
                                            await asyncio.sleep(random.uniform(0.2, 0.5))
                                            
                                            # Кликаем и ждем загрузки
                                            await next_button.click(delay=random.randint(50, 150))
                                            found_next = True
                                            break
                                
                                if not found_next:
                                    logger.warning(f"Не удалось найти кнопку 'Следующая' на странице {page_num}")
                                    url = f"https://www.google.ru/search?{urlencode(params)}"
                                    await self.playwright.navigate(page, url)
                            else:
                                # Используем прямой URL с параметрами
                                url = f"https://www.google.ru/search?{urlencode(params)}"
                                await self.playwright.navigate(page, url)
                            
                            # Ждем загрузки результатов
                            await page.wait_for_load_state("networkidle", timeout=config.browser_timeout * 1000)
                            
                            # Имитируем просмотр результатов
                            await self.playwright.human_behavior.random_scroll_page(page)
                            
                        except Exception as e:
                            logger.error(f"Ошибка при переходе на следующую страницу: {e}")
                            break
                    
                    # Get the page content
                    content = await page.content()
                    if not content:
                        logger.warning(f"Не удалось получить содержимое страницы {page_num + 1}")
                        continue
                    
                    # Перед извлечением результатов, иногда делаем случайные действия
                    if random.random() < 0.15:
                        # Находим случайную ссылку или элемент на странице
                        selectors = ["a.fl", "div.hdtb-mitem a", "div.ULSxyf", "div.MUFPAc"]
                        for selector in selectors:
                            elements = await page.query_selector_all(selector)
                            if elements:
                                random_element = random.choice(elements)
                                try:
                                    await random_element.hover()
                                    await asyncio.sleep(random.uniform(0.3, 1.0))
                                except:
                                    pass
                                break
                    
                    # Parse search results
                    urls = await self._extract_urls(content)
                    
                    # Filter and add unique URLs
                    page_unique_count = 0
                    for url in urls:
                        if self._is_valid_result(url):
                            clean_url_str = clean_url(url)
                            unique_urls.add(clean_url_str)
                            page_unique_count += 1
                            
                    logger.info(f"Найдено {len(urls)} URL на странице {page_num + 1}, "
                              f"{page_unique_count} новых уникальных, всего: {len(unique_urls)}")
                    
                    # Add some randomness to behavior - sometimes we don't check all pages
                    # Чем больше страниц проверено, тем выше вероятность остановки
                    if random.random() < 0.1 * (page_num + 1) and len(unique_urls) > 0:
                        logger.info("Случайно останавливаем поиск раньше для более естественного поведения")
                        break
                        
                    # Add a delay between pages to seem more human-like
                    if page_num < config.search_depth - 1:
                        await asyncio.sleep(random.uniform(3.0, 7.0))
                    
            finally:
                # Release page back to pool
                await self.playwright.release_page(page)
                
        except Exception as e:
            logger.error(f"Ошибка во время поиска: {e}")
            
        return unique_urls
        
    async def _extract_urls(self, content: str) -> List[str]:
        """Extract URLs from Google search results page."""
        urls = []
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Создаем список различных селекторов для различных структур Google Search
            selectors = [
                'div.yuRUbf > a',        # Основной селектор для органических результатов
                '.kCrYT > a',            # Альтернативный селектор
                'a.l',                   # Старый формат результатов
                'div.g div.r a',         # Еще один формат
                'div.tF2Cxc a',          # Новый формат Google
                'div.g div.yuRUbf a',    # Новейший формат
                'a.cz3goc',              # Еще один селектор
                '.DhN8Cf a',             # Другие возможные результаты
                '.LC20lb'                # Заголовки результатов
            ]
            
            # Пробуем все селекторы
            for selector in selectors:
                results = soup.select(selector)
                
                if results:
                    for result in results:
                        href = result.get('href')
                        # Проверяем URL и очищаем его от трекинговых параметров
                        if href:
                            # В Google ссылки могут начинаться с /url?q=
                            if href.startswith('/url?') and 'q=' in href:
                                # Извлекаем URL из редиректа Google
                                start_idx = href.find('q=') + 2
                                end_idx = href.find('&', start_idx) if '&' in href[start_idx:] else len(href)
                                href = href[start_idx:end_idx]
                            
                            # Проверяем, начинается ли URL с http или https
                            if href.startswith('http'):
                                urls.append(href)
                
            # Если все еще нет результатов, пробуем найти любые внешние ссылки
            if not urls:
                all_links = soup.find_all('a')
                for link in all_links:
                    href = link.get('href')
                    if href and href.startswith('http') and 'google' not in href:
                        urls.append(href)
                        
            # Удаляем дубликаты, сохраняя порядок
            seen = set()
            unique_urls = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            # Заменяем оригинальный список
            urls = unique_urls
                        
        except Exception as e:
            logger.error(f"Ошибка при извлечении URL: {e}")
            
        return urls
        
    def _is_valid_result(self, url: str) -> bool:
        """Check if URL is valid and not in skip list."""
        if not is_valid_url(url):
            return False
            
        domain = extract_domain(url)
        
        # Проверяем домен против списка исключений
        if not domain:
            return False
            
        # Проверяем, не в списке ли исключений
        for skip_domain in config.skip_domains:
            if skip_domain in domain:
                return False
                
        # Дополнительные проверки валидности
        # Убеждаемся, что URL не содержит нежелательных элементов
        blacklist_patterns = [
            'google.com/search', 
            'google.com/url',
            '/settings',
            '/preferences',
            '/advanced_search',
            '/intl/',
            '/sorry/',
            '/imgres?',
            '/maps?',
            '/account',
            '/webhp'
        ]
        
        for pattern in blacklist_patterns:
            if pattern in url:
                return False
                
        return True 