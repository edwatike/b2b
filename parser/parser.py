import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
import random
import os
from urllib.parse import urlparse
from .filter import process_results

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Parser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Устанавливаем базовый путь для результатов
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def is_valid_url(self, url: str) -> bool:
        """
        Проверяет, является ли URL валидным.
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def get_page_content(self, url: str) -> str:
        """Получает HTML-контент страницы."""
        try:
            logger.info(f"Fetching content from: {url}")
            response = self.session.get(url, timeout=30)  # Увеличиваем таймаут до 30 секунд
            response.raise_for_status()
            logger.info(f"Successfully fetched content from {url}")
            return response.text
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching content from {url}")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error while fetching content from {url}: {e}")
            return ""

    def parse_yandex(self, query: str, limit: int = 100, pages: int = 10) -> List[Dict[str, str]]:
        results = []
        try:
            for page in range(pages):
                if len(results) >= limit:
                    break

                url = f"https://yandex.ru/search/?text={query}&p={page}"
                logger.info(f"Parsing Yandex page {page + 1}")
                
                html = self.get_page_content(url)
                if not html:
                    continue

                soup = BeautifulSoup(html, 'html.parser')
                search_results = soup.find_all('div', {'class': 'serp-item'})

                for item in search_results:
                    if len(results) >= limit:
                        break

                    try:
                        link = item.find('a', {'class': 'link'})
                        if not link:
                            continue

                        url = link.get('href')
                        if not url:
                            continue

                        # Получаем HTML-контент найденной страницы
                        html_content = self.get_page_content(url)
                        if not html_content:
                            logger.warning(f"Could not fetch content for {url}")
                            continue

                        result = {
                            'url': url,
                            'title': link.text.strip(),
                            'html_content': html_content
                        }
                        results.append(result)
                        logger.info(f"Added result: {url}")

                    except Exception as e:
                        logger.error(f"Error processing search result: {e}")
                        continue

                time.sleep(random.uniform(1, 3))

        except Exception as e:
            logger.error(f"Error in parse_yandex: {e}")

        logger.info(f"Found {len(results)} results from Yandex")
        if results:
            print("Обработка результатов...")
            process_results(results, query)
        return results[:limit]

    def parse_google(self, query: str, limit: int = 100, pages: int = 10) -> List[Dict[str, str]]:
        results = []
        try:
            for page in range(pages):
                if len(results) >= limit:
                    break

                start = page * 10
                url = f"https://www.google.com/search?q={query}&start={start}"
                logger.info(f"Parsing Google page {page + 1}")

                html = self.get_page_content(url)
                if not html:
                    continue

                soup = BeautifulSoup(html, 'html.parser')
                search_results = soup.find_all('div', {'class': 'g'})

                for item in search_results:
                    if len(results) >= limit:
                        break

                    try:
                        link = item.find('a')
                        if not link:
                            continue

                        url = link.get('href')
                        if not url or not url.startswith('http'):
                            continue

                        # Получаем HTML-контент найденной страницы
                        html_content = self.get_page_content(url)
                        if not html_content:
                            logger.warning(f"Could not fetch content for {url}")
                            continue

                        result = {
                            'url': url,
                            'title': link.text.strip(),
                            'html_content': html_content
                        }
                        results.append(result)
                        logger.info(f"Added result: {url}")

                    except Exception as e:
                        logger.error(f"Error processing search result: {e}")
                        continue

                time.sleep(random.uniform(1, 3))

        except Exception as e:
            logger.error(f"Error in parse_google: {e}")

        logger.info(f"Found {len(results)} results from Google")
        if results:
            print("Обработка результатов...")
            process_results(results, query)
        return results[:limit]

    def search(self, query: str, limit: int = 100, pages: int = 10, engine: str = "yandex") -> List[Dict[str, str]]:
        if engine.lower() == "yandex":
            return self.parse_yandex(query, limit, pages)
        elif engine.lower() == "google":
            return self.parse_google(query, limit, pages)
        else:
            raise ValueError("Неподдерживаемая поисковая система") 