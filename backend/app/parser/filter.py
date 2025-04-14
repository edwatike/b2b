import os
import logging
import traceback
from typing import Dict, List
from urllib.parse import urlparse
from .storage import Storage

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Создаем директории для сохранения результатов
base_dir = os.path.join(os.getcwd(), "results")
suppliers_dir = os.path.join(base_dir, "suppliers")
others_dir = os.path.join(base_dir, "others")
sites_dir = os.path.join(base_dir, "sites")

logger.debug(f"Текущая рабочая директория: {os.getcwd()}")
logger.debug(f"Полный путь к base_dir: {os.path.abspath(base_dir)}")

# Создаем все необходимые директории
for directory in [base_dir, suppliers_dir, others_dir, sites_dir]:
    try:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Директория создана/существует: {directory}")
        logger.debug(f"Права доступа: {oct(os.stat(directory).st_mode)}")
    except Exception as e:
        logger.error(f"Ошибка при создании директории {directory}: {e}")
        logger.error(traceback.format_exc())

# Инициализация хранилища
try:
    storage = Storage()
    logger.info("Хранилище успешно инициализировано")
except Exception as e:
    logger.error(f"Ошибка при инициализации хранилища: {e}")
    logger.error(traceback.format_exc())
    raise

def save_html_to_file(domain: str, html: str, category: str) -> None:
    """Сохраняет HTML-контент в файл"""
    logger.debug(f"=== Начало save_html_to_file ===")
    logger.debug(f"Домен: {domain}")
    logger.debug(f"Категория: {category}")
    logger.debug(f"Размер HTML: {len(html) if html else 0} байт")
    
    try:
        # Определяем путь к файлу
        target_dir = suppliers_dir if category == 'suppliers' else others_dir
        file_path = os.path.join(target_dir, f"{domain}.html")
        
        logger.debug(f"Целевая директория: {target_dir}")
        logger.debug(f"Полный путь к файлу: {file_path}")
        logger.debug(f"Директория существует: {os.path.exists(target_dir)}")
        logger.debug(f"Права доступа к директории: {oct(os.stat(target_dir).st_mode)}")
        
        if not html:
            logger.warning("Получен пустой HTML-контент")
            return
            
        # Проверяем права доступа к директории
        if not os.access(target_dir, os.W_OK):
            logger.error(f"Нет прав на запись в директорию: {target_dir}")
            return
            
        # Сохраняем HTML в файл
        logger.debug("Начало записи в файл...")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            logger.info(f"HTML-контент успешно сохранен в файл: {file_path}")
            logger.info(f"Размер файла: {file_size} байт")
        else:
            logger.error(f"Файл не был создан: {file_path}")
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении HTML в файл: {str(e)}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(traceback.format_exc())
        if isinstance(e, PermissionError):
            logger.error(f"Ошибка прав доступа к {file_path}")
        elif isinstance(e, FileNotFoundError):
            logger.error(f"Директория не найдена: {target_dir}")
        elif isinstance(e, IOError):
            logger.error(f"Ошибка ввода-вывода при работе с {file_path}")

def has_company_markers(html: str) -> bool:
    """Проверяет наличие маркеров компании в HTML-контенте"""
    logger.debug("=== Начало has_company_markers ===")
    
    if not html:
        logger.warning("Получен пустой HTML-контент")
        return False
        
    company_markers = [
        'ИНН',
        'ООО',
        'ОАО',
        'АО',
        'ИП',
        'реквизиты'
    ]
    
    logger.debug(f"Размер HTML: {len(html)} байт")
    logger.debug(f"Поиск маркеров: {company_markers}")
    
    found_markers = []
    for marker in company_markers:
        if marker.lower() in html.lower():
            found_markers.append(marker)
            
    if found_markers:
        logger.info(f"Найдены маркеры компании: {found_markers}")
        return True
    else:
        logger.debug("Маркеры компании не найдены")
        return False

def get_domain_from_url(url: str) -> str:
    """Извлекает домен из URL"""
    logger.debug(f"=== Начало get_domain_from_url ===")
    logger.debug(f"URL: {url}")
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        logger.debug(f"Результат парсинга:")
        logger.debug(f"- scheme: {parsed.scheme}")
        logger.debug(f"- netloc: {parsed.netloc}")
        logger.debug(f"- path: {parsed.path}")
        
        if not domain:
            logger.error(f"Не удалось извлечь домен из URL: {url}")
            return ""
            
        logger.info(f"Успешно извлечен домен: {domain}")
        return domain
        
    except Exception as e:
        logger.error(f"Ошибка при разборе URL {url}: {e}")
        logger.error(traceback.format_exc())
        return ""

async def process_results(results: List[Dict], keyword: str) -> None:
    """Обрабатывает результаты поиска и сохраняет их в соответствующую категорию"""
    logger.debug(f"\n=== Начало process_results ===")
    logger.debug(f"Количество результатов: {len(results)}")
    logger.debug(f"Ключевое слово: {keyword}")
    logger.debug(f"Тип объекта results: {type(results)}")
    logger.debug(f"Содержимое results: {results}")

    suppliers_count = 0
    others_count = 0
    errors_count = 0
    processed_count = 0

    for idx, result in enumerate(results, 1):
        try:
            logger.debug(f"\n--- Обработка результата {idx}/{len(results)} ---")
            logger.debug(f"Содержимое результата: {result}")
            
            url = result.get('url')
            html = result.get('html_content')
            
            logger.info(f"Обработка URL: {url}")
            logger.debug(f"Тип html_content: {type(html)}")
            logger.debug(f"Размер html_content: {len(html) if html else 0} байт")
            logger.debug(f"Первые 100 символов html_content: {html[:100] if html else ''}")
            
            if not url:
                logger.error("Пропуск: отсутствует URL")
                errors_count += 1
                continue
                
            if not html:
                logger.error(f"Пропуск: отсутствует HTML-контент для {url}")
                errors_count += 1
                continue

            domain = get_domain_from_url(url)
            if not domain:
                logger.error(f"Пропуск: не удалось извлечь домен из URL {url}")
                errors_count += 1
                continue
                
            logger.info(f"Извлечённый домен: {domain}")
            
            # Определяем категорию на основе HTML-контента
            logger.debug("Начало проверки маркеров компании...")
            is_supplier = has_company_markers(html)
            category = 'suppliers' if is_supplier else 'others'
            logger.info(f"Определена категория: {category}")
            
            # Сохраняем в хранилище
            try:
                logger.info(f"Вызов storage.save_site для домена {domain}...")
                logger.debug(f"Параметры:")
                logger.debug(f"- domain: {domain}")
                logger.debug(f"- category: {category}")
                logger.debug(f"- keyword: {keyword}")
                logger.debug(f"- размер HTML: {len(html)} байт")
                
                await storage.save_site(domain, html, keyword, category)
                
                if category == 'suppliers':
                    suppliers_count += 1
                else:
                    others_count += 1
                    
                processed_count += 1
                logger.info(f"Сайт {domain} успешно обработан и сохранён")
                
            except Exception as e:
                logger.error(f"Ошибка при сохранении сайта {domain}: {e}")
                logger.error(traceback.format_exc())
                errors_count += 1
                continue
            
        except Exception as e:
            logger.error(f"Ошибка при обработке результата {idx}: {e}")
            logger.error(traceback.format_exc())
            errors_count += 1
            continue
            
    logger.info("\n=== Итоги обработки результатов ===")
    logger.info(f"Всего обработано: {processed_count}/{len(results)}")
    logger.info(f"Найдено поставщиков: {suppliers_count}")
    logger.info(f"Найдено других сайтов: {others_count}")
    logger.info(f"Количество ошибок: {errors_count}")
    
    if errors_count > 0:
        logger.warning("Были ошибки при обработке результатов!")