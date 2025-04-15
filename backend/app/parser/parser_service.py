from typing import List, Dict, Optional, Union, Set
from urllib.parse import urlparse
from sqlalchemy import select
from app.db.session import async_session
from app.models.search_result import SearchResult
from .playwright_runner import PlaywrightRunner
from .parser_config import ParserConfig
from .site_classifier import SiteClassifier
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
        self.site_classifier = SiteClassifier()  # Добавляем классификатор сайтов
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
        
        # Директории для категорий сайтов
        self.suppliers_dir = os.path.join(self.results_dir, "suppliers")
        self.others_dir = os.path.join(self.results_dir, "others")
        self.sites_dir = os.path.join(self.results_dir, "sites")
        
        # Создаем директории для категорий, если они не существуют
        for directory in [self.suppliers_dir, self.others_dir, self.sites_dir]:
            os.makedirs(directory, exist_ok=True)
            
        # Множество уже обработанных доменов для избежания дублирования
        self.processed_domains: Set[str] = set()
        
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
            
            # Удаляем дубликаты по домену
            unique_results = await self.remove_domain_duplicates(results)
            logger.info(f"После удаления дубликатов: {len(unique_results)} из {len(results)} результатов")
            
            # Классифицируем сайты
            await self.classify_sites(unique_results, keyword)
            
            # Сохраняем результаты в базу данных
            if unique_results:
                await self.save_results(keyword, unique_results)
                logger.info(f"Сохранено {len(unique_results)} результатов для запроса '{keyword}'")
            
            # Ограничиваем количество результатов
            final_results = unique_results[:max_results]
            
            # Получаем статистику классификации
            classification_stats = self.site_classifier.get_stats()
            
            return {
                "results": final_results,
                "total": len(final_results),
                "cached": 0,
                "new": len(final_results),
                "search_mode": search_mode,  # Используем текущий режим поиска
                "suppliers": classification_stats['suppliers_found'],
                "others": classification_stats['others_found'],
                "errors": classification_stats['errors'],
                "duplicates_removed": len(results) - len(unique_results)
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

    async def remove_domain_duplicates(self, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Удаляет дубликаты по домену из списка результатов.
        
        Args:
            results: Список результатов поиска
            
        Returns:
            List[Dict[str, str]]: Список уникальных результатов
        """
        unique_results = []
        seen_domains = set()
        
        for result in results:
            url = result.get("url", "")
            if not url:
                continue
                
            try:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                # Удаляем www. из домена, если есть
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Проверяем, был ли уже обработан этот домен
                if domain in seen_domains or domain in self.processed_domains:
                    logger.info(f"Пропускаем дубликат домена: {domain}")
                    continue
                
                # Добавляем домен в множество обработанных
                seen_domains.add(domain)
                
                # Добавляем результат в список уникальных
                unique_results.append(result)
                
                # Извлекаем и добавляем домен в результат
                result["domain"] = domain
                
            except Exception as e:
                logger.error(f"Ошибка при обработке URL {url}: {str(e)}")
                # Добавляем результат, даже если не смогли извлечь домен
                unique_results.append(result)
        
        return unique_results
        
    async def classify_sites(self, results: List[Dict[str, str]], keyword: str) -> None:
        """
        Классифицирует сайты и сохраняет их в соответствующие файлы.
        
        Args:
            results: Список результатов поиска
            keyword: Ключевое слово для поиска
        """
        try:
            logger.info(f"Классифицируем {len(results)} сайтов")
            
            # Классифицируем сайты
            suppliers, others = await self.site_classifier.classify_batch(results)
            
            logger.info(f"Классификация завершена: {len(suppliers)} поставщиков, {len(others)} других сайтов")
            
            # Сохраняем поставщиков
            if suppliers:
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword)
                
                # Сохраняем в JSON
                suppliers_file = os.path.join(self.suppliers_dir, f"{safe_keyword}_{timestamp}.json")
                with open(suppliers_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "query": keyword,
                        "timestamp": timestamp,
                        "count": len(suppliers),
                        "results": suppliers
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Поставщики сохранены в файл: {suppliers_file}")
                
            # Сохраняем другие сайты
            if others:
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword)
                
                # Сохраняем в JSON
                others_file = os.path.join(self.others_dir, f"{safe_keyword}_{timestamp}.json")
                with open(others_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "query": keyword,
                        "timestamp": timestamp,
                        "count": len(others),
                        "results": others
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Другие сайты сохранены в файл: {others_file}")
                
        except Exception as e:
            logger.error(f"Ошибка при классификации сайтов: {str(e)}")

    async def save_results_to_file(self, keyword: str, results: List[Dict[str, str]], format: str = "json", classify: bool = True) -> str:
        """Сохраняет результаты поиска в файл.
        
        Args:
            keyword: Ключевое слово для поиска
            results: Список результатов поиска
            format: Формат файла (json, csv, txt)
            classify: Классифицировать ли сайты
            
        Returns:
            str: Путь к файлу с результатами
        """
        try:
            # Создаем уникальное имя файла на основе запроса и времени
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            # Заменяем недопустимые символы в имени файла
            safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword)
            
            # Если нужно классифицировать, делаем это
            if classify and results:
                await self.classify_sites(results, keyword)
            
            # Определяем директорию для сохранения (общая, без классификации)
            target_dir = self.sites_dir
            
            if format.lower() == "json":
                filename = f"{safe_keyword}_{timestamp}.json"
                filepath = os.path.join(target_dir, filename)
                
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
                filepath = os.path.join(target_dir, filename)
                
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
                filepath = os.path.join(target_dir, filename)
                
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