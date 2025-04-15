from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Optional
import logging
from ..parser.models import SearchRequest, SearchResponse, SearchResult
from ..parser.parser_service import ParserService
from ..parser.playwright_runner import PlaywrightRunner
from ..parser.config.parser_config import config
from pydantic import BaseModel, validator
import os
from enum import Enum
from fastapi.responses import FileResponse
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parser", tags=["parser"])

# Global instances
playwright_runner = None
parser_service = ParserService()

class SearchRequest(BaseModel):
    query: str
    limit: int = 100  # Увеличиваем лимит по умолчанию
    pages: int = 1
    save_results: bool = False  # Флаг для сохранения результатов
    file_format: str = "json"   # Формат файла для сохранения

    @validator('limit')
    def validate_limit(cls, v):
        if v <= 0:
            raise ValueError("Лимит должен быть положительным числом")
        if v > 200:  # Устанавливаем максимальный лимит
            logger.warning(f"Запрошен лимит {v}, ограничиваем до 200")
            return 200
        return v

    @validator('pages')
    def validate_pages(cls, v):
        if v <= 0:
            raise ValueError("Количество страниц должно быть положительным числом")
        if v > 20:  # Устанавливаем максимальное количество страниц
            logger.warning(f"Запрошено {v} страниц, ограничиваем до 20")
            return 20
        return v

class SearchResponse(BaseModel):
    results: List[Dict[str, str]]
    total: int
    cached: int
    new: int
    search_mode: str
    suppliers: Optional[int] = 0
    others: Optional[int] = 0
    duplicates_removed: Optional[int] = 0
    errors: Optional[int] = 0
    saved_to_file: Optional[str] = None

class FileFormat(str, Enum):
    json = "json"
    csv = "csv"
    txt = "txt"

class SaveRequest(BaseModel):
    query: str
    file_format: FileFormat = FileFormat.json

@router.on_event("startup")
async def startup_event():
    """Initialize parser service on startup."""
    global playwright_runner
    playwright_runner = PlaywrightRunner(config)
    await playwright_runner.initialize()
    logger.info("✅ Parser service initialized")

@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    global playwright_runner
    if playwright_runner:
        await playwright_runner.cleanup()
    logger.info("✅ Parser service cleaned up")

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Выполняет поиск по запросу.
    
    Args:
        request: Запрос на поиск, содержащий:
            - query: Поисковый запрос
            - limit: Максимальное количество результатов
            - pages: Количество страниц для парсинга
            - save_results: Сохранять ли результаты в файл
            - file_format: Формат файла для сохранения
            
    Returns:
        SearchResponse: Результаты поиска
    """
    try:
        logger.info(f"Получен запрос на поиск: {request.query}")
        logger.info(f"Максимальное количество результатов: {request.limit}")
        logger.info(f"Количество страниц для парсинга: {request.pages}")
        logger.info(f"Сохранять результаты: {request.save_results}")
        
        if request.save_results:
            logger.info(f"Формат файла для сохранения: {request.file_format}")

        current_mode = parser_service.get_current_search_mode()
        logger.info(f"Текущий режим поиска: {current_mode}")

        results = await parser_service.search_and_save(
            keyword=request.query,
            max_results=request.limit,
            pages=request.pages
        )
        logger.info(f"Получены результаты: {results}")

        # Сохраняем результаты в файл, если запрошено
        saved_file = None
        if request.save_results and results and "results" in results:
            try:
                saved_file = await parser_service.save_results_to_file(
                    keyword=request.query,
                    results=results["results"],
                    format=request.file_format
                )
                logger.info(f"Результаты сохранены в файл: {saved_file}")
                
                # Добавляем информацию о сохраненном файле в результаты
                results["saved_to_file"] = os.path.basename(saved_file)
                
            except Exception as e:
                logger.error(f"Ошибка при сохранении результатов: {str(e)}")
                results["save_error"] = str(e)
        
        # Проверяем структуру результатов
        if not isinstance(results, dict):
            logger.error(f"Неверный тип результатов: {type(results)}")
            raise ValueError("Результаты должны быть словарем")

        if "results" not in results:
            logger.error(f"В результатах отсутствует ключ 'results': {results}")
            raise ValueError("В результатах отсутствует ключ 'results'")

        if not isinstance(results["results"], list):
            logger.error(f"results['results'] не является списком: {type(results['results'])}")
            raise ValueError("results['results'] должен быть списком")

        logger.info(f"Поиск завершен, найдено результатов: {len(results['results'])}")
        logger.info(f"Отправляем ответ: {results}")
        return results

    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/save")
async def save_last_search(request: SaveRequest):
    """Сохраняет результаты последнего поиска в файл.
    
    Args:
        request: Запрос на сохранение, содержащий:
            - query: Поисковый запрос
            - file_format: Формат файла для сохранения
            
    Returns:
        FileResponse: Файл с результатами
    """
    try:
        logger.info(f"Получен запрос на сохранение результатов поиска: {request.query}")
        logger.info(f"Формат файла: {request.file_format}")
        
        # Получаем результаты из кэша
        cached_results = await parser_service.get_cached_results(request.query, 200)
        
        if not cached_results or not cached_results.get("results"):
            raise HTTPException(status_code=404, detail=f"Результаты для запроса '{request.query}' не найдены")
        
        # Сохраняем результаты в файл
        saved_file = await parser_service.save_results_to_file(
            keyword=request.query,
            results=cached_results["results"],
            format=request.file_format
        )
        
        logger.info(f"Результаты сохранены в файл: {saved_file}")
        
        # Возвращаем файл для скачивания
        return FileResponse(
            path=saved_file,
            filename=os.path.basename(saved_file),
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении результатов: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/results/{filename}")
async def get_saved_results(filename: str):
    """Возвращает сохраненные результаты поиска.
    
    Args:
        filename: Имя файла с результатами
            
    Returns:
        FileResponse: Файл с результатами
    """
    try:
        logger.info(f"Получен запрос на получение файла: {filename}")
        
        # Проверяем наличие файла
        results_dir = parser_service.results_dir
        file_path = os.path.join(results_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Файл {filename} не найден")
        
        logger.info(f"Файл найден: {file_path}")
        
        # Определяем MIME-тип
        if filename.endswith(".json"):
            media_type = "application/json"
        elif filename.endswith(".csv"):
            media_type = "text/csv"
        elif filename.endswith(".txt"):
            media_type = "text/plain"
        else:
            media_type = "application/octet-stream"
        
        # Возвращаем файл для скачивания
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении файла: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/results")
async def list_saved_results():
    """Возвращает список сохраненных результатов поиска.
    
    Returns:
        List[Dict]: Список файлов с результатами
    """
    try:
        logger.info("Получен запрос на получение списка файлов с результатами")
        
        # Получаем список файлов
        results_dir = parser_service.results_dir
        files = []
        
        for filename in os.listdir(results_dir):
            if filename.endswith((".json", ".csv", ".txt")):
                file_path = os.path.join(results_dir, filename)
                
                # Получаем информацию о файле
                file_info = {
                    "filename": filename,
                    "size": os.path.getsize(file_path),
                    "created": os.path.getctime(file_path),
                    "format": filename.split(".")[-1]
                }
                
                # Если это JSON, извлекаем информацию о запросе
                if filename.endswith(".json"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            file_info["query"] = data.get("query", "")
                            file_info["count"] = data.get("count", 0)
                            file_info["timestamp"] = data.get("timestamp", "")
                    except:
                        pass
                
                files.append(file_info)
        
        # Сортируем по времени создания (новые сначала)
        files.sort(key=lambda x: x["created"], reverse=True)
        
        logger.info(f"Найдено файлов: {len(files)}")
        
        return {
            "count": len(files),
            "files": files
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/mode", response_model=dict)
async def get_search_mode():
    """Возвращает текущий режим поиска."""
    current_mode = parser_service.get_current_search_mode()
    return {"mode": current_mode}

@router.get("/search/results/suppliers")
async def list_supplier_results():
    """Возвращает список сохраненных результатов поиска поставщиков.
    
    Returns:
        Dict: Список файлов с результатами поставщиков
    """
    try:
        logger.info("Получен запрос на получение списка файлов с результатами поставщиков")
        
        # Получаем список файлов из директории suppliers
        results_dir = os.path.join(parser_service.results_dir, "suppliers")
        files = []
        
        if os.path.exists(results_dir):
            for filename in os.listdir(results_dir):
                if filename.endswith((".json", ".csv", ".txt")):
                    file_path = os.path.join(results_dir, filename)
                    
                    # Получаем информацию о файле
                    file_info = {
                        "filename": filename,
                        "size": os.path.getsize(file_path),
                        "created": os.path.getctime(file_path),
                        "format": filename.split(".")[-1],
                        "category": "suppliers"
                    }
                    
                    # Если это JSON, извлекаем информацию о запросе
                    if filename.endswith(".json"):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                file_info["query"] = data.get("query", "")
                                file_info["count"] = data.get("count", 0)
                                file_info["timestamp"] = data.get("timestamp", "")
                        except:
                            pass
                    
                    files.append(file_info)
        
        # Сортируем по времени создания (новые сначала)
        files.sort(key=lambda x: x["created"], reverse=True)
        
        logger.info(f"Найдено файлов поставщиков: {len(files)}")
        
        return {
            "count": len(files),
            "files": files
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов поставщиков: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/results/others")
async def list_other_results():
    """Возвращает список сохраненных результатов поиска других сайтов.
    
    Returns:
        Dict: Список файлов с результатами других сайтов
    """
    try:
        logger.info("Получен запрос на получение списка файлов с результатами других сайтов")
        
        # Получаем список файлов из директории others
        results_dir = os.path.join(parser_service.results_dir, "others")
        files = []
        
        if os.path.exists(results_dir):
            for filename in os.listdir(results_dir):
                if filename.endswith((".json", ".csv", ".txt")):
                    file_path = os.path.join(results_dir, filename)
                    
                    # Получаем информацию о файле
                    file_info = {
                        "filename": filename,
                        "size": os.path.getsize(file_path),
                        "created": os.path.getctime(file_path),
                        "format": filename.split(".")[-1],
                        "category": "others"
                    }
                    
                    # Если это JSON, извлекаем информацию о запросе
                    if filename.endswith(".json"):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                file_info["query"] = data.get("query", "")
                                file_info["count"] = data.get("count", 0)
                                file_info["timestamp"] = data.get("timestamp", "")
                        except:
                            pass
                    
                    files.append(file_info)
        
        # Сортируем по времени создания (новые сначала)
        files.sort(key=lambda x: x["created"], reverse=True)
        
        logger.info(f"Найдено файлов других сайтов: {len(files)}")
        
        return {
            "count": len(files),
            "files": files
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов других сайтов: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/search/results/classified")
async def list_classified_results():
    """Возвращает список всех классифицированных результатов поиска.
    
    Returns:
        Dict: Список файлов с классифицированными результатами
    """
    try:
        logger.info("Получен запрос на получение списка всех классифицированных файлов")
        
        # Получаем список файлов из директории suppliers и others
        suppliers_dir = os.path.join(parser_service.results_dir, "suppliers")
        others_dir = os.path.join(parser_service.results_dir, "others")
        files = []
        
        # Собираем файлы поставщиков
        if os.path.exists(suppliers_dir):
            for filename in os.listdir(suppliers_dir):
                if filename.endswith((".json", ".csv", ".txt")):
                    file_path = os.path.join(suppliers_dir, filename)
                    
                    # Получаем информацию о файле
                    file_info = {
                        "filename": filename,
                        "size": os.path.getsize(file_path),
                        "created": os.path.getctime(file_path),
                        "format": filename.split(".")[-1],
                        "category": "suppliers",
                        "path": f"suppliers/{filename}"
                    }
                    
                    # Если это JSON, извлекаем информацию о запросе
                    if filename.endswith(".json"):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                file_info["query"] = data.get("query", "")
                                file_info["count"] = data.get("count", 0)
                                file_info["timestamp"] = data.get("timestamp", "")
                        except:
                            pass
                    
                    files.append(file_info)
        
        # Собираем файлы других сайтов
        if os.path.exists(others_dir):
            for filename in os.listdir(others_dir):
                if filename.endswith((".json", ".csv", ".txt")):
                    file_path = os.path.join(others_dir, filename)
                    
                    # Получаем информацию о файле
                    file_info = {
                        "filename": filename,
                        "size": os.path.getsize(file_path),
                        "created": os.path.getctime(file_path),
                        "format": filename.split(".")[-1],
                        "category": "others",
                        "path": f"others/{filename}"
                    }
                    
                    # Если это JSON, извлекаем информацию о запросе
                    if filename.endswith(".json"):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                file_info["query"] = data.get("query", "")
                                file_info["count"] = data.get("count", 0)
                                file_info["timestamp"] = data.get("timestamp", "")
                        except:
                            pass
                    
                    files.append(file_info)
        
        # Сортируем по времени создания (новые сначала)
        files.sort(key=lambda x: x["created"], reverse=True)
        
        logger.info(f"Найдено классифицированных файлов: {len(files)}")
        
        # Группируем файлы по запросам
        queries = {}
        for file in files:
            query = file.get("query", "unknown")
            if query not in queries:
                queries[query] = {
                    "query": query,
                    "suppliers": [],
                    "others": [],
                    "total_suppliers": 0,
                    "total_others": 0
                }
            
            if file["category"] == "suppliers":
                queries[query]["suppliers"].append(file)
                queries[query]["total_suppliers"] += file.get("count", 0)
            else:
                queries[query]["others"].append(file)
                queries[query]["total_others"] += file.get("count", 0)
        
        return {
            "count": len(files),
            "queries": list(queries.values()),
            "files": files
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка классифицированных файлов: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/search/results/category/{category}/{filename}")
async def get_category_results(category: str, filename: str):
    """Возвращает файл с результатами поиска из указанной категории.
    
    Args:
        category: Категория (suppliers или others)
        filename: Имя файла с результатами
            
    Returns:
        FileResponse: Файл с результатами
    """
    try:
        logger.info(f"Получен запрос на получение файла {filename} из категории {category}")
        
        # Проверяем категорию
        if category not in ["suppliers", "others", "sites"]:
            raise HTTPException(status_code=400, detail=f"Недопустимая категория: {category}")
        
        # Определяем директорию для категории
        category_dir = os.path.join(parser_service.results_dir, category)
        
        # Проверяем наличие файла
        file_path = os.path.join(category_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Файл {filename} не найден в категории {category}")
        
        logger.info(f"Файл найден: {file_path}")
        
        # Определяем MIME-тип
        if filename.endswith(".json"):
            media_type = "application/json"
        elif filename.endswith(".csv"):
            media_type = "text/csv"
        elif filename.endswith(".txt"):
            media_type = "text/plain"
        else:
            media_type = "application/octet-stream"
        
        # Возвращаем файл для скачивания
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении файла: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e)) 