from typing import List, Dict, Optional, Union
from urllib.parse import urlparse
from sqlalchemy import select
from app.db.session import async_session
from app.models.search_result import SearchResult
from .playwright_runner import PlaywrightRunner
from .parser_config import ParserConfig
from playwright.async_api import async_playwright
import logging
import asyncio
import os
from collections import defaultdict
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ParserService:
    def __init__(self):
        self.config = ParserConfig()
        self.config.validate()  # Проверяем корректность настроек
        self.playwright_runner = PlaywrightRunner(config=self.config)
        self.results_dir = "/app/results"  # Путь к директории результатов внутри контейнера
        
        # Проверяем и создаем директорию для результатов, если она не существует
        if not os.path.exists(self.results_dir):
            try:
                os.makedirs(self.results_dir, exist_ok=True)
                logger.info(f"Создана директория для результатов: {self.results_dir}")
            except Exception as e:
                logger.error(f"Не удалось создать директорию для результатов: {str(e)}")
                # Используем резервный путь
                self.results_dir = "results"
                os.makedirs(self.results_dir, exist_ok=True)
        
    def get_current_search_mode(self) -> str:
        """Получает текущий режим поиска из переменной окружения или конфига."""
        return os.getenv("SEARCH_MODE", self.config.search_mode)
        
    async def search_and_save(self, keyword: str, max_results: int = None, pages: int = 1) -> Dict[str, Union[List[Dict[str, str]], int, str]]:
        """Выполняет поиск и сохраняет результаты в базу данных.
        
        Args:
            keyword: Ключевое слово для поиска
            max_results: Максимальное количество результатов (если None, используется значение из конфига)
            pages: Количество страниц для парсинга
            
        Returns:
            Dict[str, Union[List[Dict[str, str]], int, str]]: Результаты поиска
        """
        try:
            # Используем значения из конфига, если параметры не указаны
            max_results = max_results or self.config.max_results
            search_mode = self.get_current_search_mode()

            logger.info(f"Начинаем поиск с настройками: mode={search_mode}, max_results={max_results}, pages={pages}")

            # Проверяем кэш
            cached_results = await self.get_cached_results(keyword, max_results)
            if cached_results:
                logger.info(f"Найдены кэшированные результаты для запроса '{keyword}'")
                return cached_results

            # Выполняем поиск в соответствии с настройками
            if search_mode == "both":
                results = await self.parallel_search(keyword, max_results, pages)
            else:
                if search_mode == "yandex":
                    from .search_yandex import search_yandex
                    results = await search_yandex(query=keyword, limit=max_results, pages=pages)
                elif search_mode == "google":
                    from .search_google import search_google
                    results = await search_google(query=keyword, limit=max_results, pages=pages)
                else:
                    raise ValueError(f"Недопустимый режим поиска: {search_mode}")
            
            # Сохраняем результаты в базу данных
            if results:
                await self.save_results(keyword, results)
                logger.info(f"Сохранено {len(results)} результатов для запроса '{keyword}'")
            
            # Ограничиваем количество результатов
            final_results = results[:max_results]
            
            return {
                "results": final_results,
                "total": len(final_results),
                "cached": 0,
                "new": len(final_results),
                "search_mode": search_mode  # Используем текущий режим поиска
            }
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска: {str(e)}")
            raise

    async def parallel_search(self, keyword: str, max_results: int, pages: int = 1) -> List[Dict[str, str]]:
        """Выполняет параллельный поиск в обеих поисковых системах.
        
        Args:
            keyword: Ключевое слово для поиска
            max_results: Максимальное количество результатов
            pages: Количество страниц для парсинга
            
        Returns:
            List[Dict[str, str]]: Объединенный список результатов поиска
        """
        try:
            from .search_yandex import search_yandex
            from .search_google import search_google

            logger.info(f"Запускаем параллельный поиск в Яндекс и Google на {pages} страницах")

            # Запускаем поиск параллельно
            yandex_task = search_yandex(query=keyword, limit=max_results, pages=pages)
            google_task = search_google(query=keyword, limit=max_results, pages=pages)
            
            yandex_results, google_results = await asyncio.gather(
                yandex_task,
                google_task,
                return_exceptions=True
            )

            # Обрабатываем результаты
            all_results = []
            seen_urls = set()  # Для дедупликации результатов

            # Добавляем результаты Яндекса
            if isinstance(yandex_results, list):
                logger.info(f"Получено {len(yandex_results)} результатов от Яндекса")
                for result in yandex_results:
                    if result["url"] not in seen_urls:
                        seen_urls.add(result["url"])
                        all_results.append(result)

            # Добавляем результаты Google
            if isinstance(google_results, list):
                logger.info(f"Получено {len(google_results)} результатов от Google")
                for result in google_results:
                    if result["url"] not in seen_urls:
                        seen_urls.add(result["url"])
                        all_results.append(result)

            # Сортируем результаты по релевантности
            all_results.sort(key=lambda x: len(x.get("title", "")), reverse=True)
            
            # Ограничиваем количество результатов
            final_results = all_results[:max_results]
            logger.info(f"Всего найдено уникальных результатов: {len(final_results)}")
            
            return final_results

        except Exception as e:
            logger.error(f"Ошибка при параллельном поиске: {str(e)}")
            raise

    async def get_cached_results(self, keyword: str, max_results: int) -> Optional[Dict[str, Union[List[Dict[str, str]], int, str]]]:
        """Проверяет наличие кэшированных результатов поиска.
        
        Args:
            keyword: Ключевое слово для поиска
            max_results: Максимальное количество результатов
            
        Returns:
            Optional[Dict[str, Union[List[Dict[str, str]], int, str]]]: Словарь с кэшированными результатами или None
        """
        try:
            async with async_session() as session:
                # Получаем кэшированные результаты
                results = await session.execute(
                    select(SearchResult)
                    .where(SearchResult.query == keyword)
                    .limit(max_results)
                )
                cached_results = results.scalars().all()
                
                if cached_results:
                    results_list = [{
                        "url": result.url,
                        "title": result.title or "",
                        "domain": result.domain or ""
                    } for result in cached_results]
                    
                    return {
                        "results": results_list,
                        "total": len(results_list),
                        "cached": len(results_list),
                        "new": 0,
                        "search_mode": self.get_current_search_mode()
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка при получении кэшированных результатов: {str(e)}")
            
        return None
        
    async def save_results(self, keyword: str, results: List[Dict[str, str]]) -> None:
        """Сохраняет результаты поиска в базу данных.
        
        Args:
            keyword: Ключевое слово для поиска
            results: Список результатов поиска
        """
        try:
            async with async_session() as session:
                for result in results:
                    # Извлекаем домен из URL
                    parsed_url = urlparse(result["url"])
                    domain = parsed_url.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    
                    search_result = SearchResult(
                        url=result["url"],
                        result_url=result["url"],  # Используем тот же URL
                        title=result.get("title", ""),
                        domain=domain,
                        query=keyword
                    )
                    session.add(search_result)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов: {str(e)}")
            raise 

    async def save_results_to_file(self, keyword: str, results: List[Dict[str, str]], format: str = "json") -> str:
        """Сохраняет результаты поиска в файл.
        
        Args:
            keyword: Ключевое слово для поиска
            results: Список результатов поиска
            format: Формат файла (json, csv, txt)
            
        Returns:
            str: Путь к файлу с результатами
        """
        try:
            # Создаем уникальное имя файла на основе запроса и времени
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            # Заменяем недопустимые символы в имени файла
            safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword)
            
            if format.lower() == "json":
                filename = f"{safe_keyword}_{timestamp}.json"
                filepath = os.path.join(self.results_dir, filename)
                
                # Формируем данные для сохранения
                data = {
                    "query": keyword,
                    "timestamp": timestamp,
                    "count": len(results),
                    "results": results
                }
                
                # Сохраняем в JSON
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Результаты сохранены в файл: {filepath}")
                return filepath
                
            elif format.lower() == "csv":
                filename = f"{safe_keyword}_{timestamp}.csv"
                filepath = os.path.join(self.results_dir, filename)
                
                # Сохраняем в CSV
                with open(filepath, "w", encoding="utf-8") as f:
                    # Записываем заголовки
                    f.write("title,url,domain\n")
                    
                    # Записываем данные
                    for result in results:
                        title = result.get("title", "").replace('"', '""')  # Экранируем кавычки
                        url = result.get("url", "")
                        domain = result.get("domain", "")
                        f.write(f'"{title}",{url},{domain}\n')
                
                logger.info(f"Результаты сохранены в файл: {filepath}")
                return filepath
                
            elif format.lower() == "txt":
                filename = f"{safe_keyword}_{timestamp}.txt"
                filepath = os.path.join(self.results_dir, filename)
                
                # Сохраняем в текстовый файл
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"Результаты поиска по запросу: {keyword}\n")
                    f.write(f"Дата и время: {timestamp}\n")
                    f.write(f"Количество результатов: {len(results)}\n\n")
                    
                    for i, result in enumerate(results, 1):
                        f.write(f"{i}. {result.get('title', '')}\n")
                        f.write(f"   URL: {result.get('url', '')}\n")
                        f.write(f"   Домен: {result.get('domain', '')}\n\n")
                
                logger.info(f"Результаты сохранены в файл: {filepath}")
                return filepath
            
            else:
                logger.error(f"Неподдерживаемый формат файла: {format}")
                raise ValueError(f"Неподдерживаемый формат файла: {format}")
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов: {str(e)}")
            raise 