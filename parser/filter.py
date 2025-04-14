import os
import re
import logging
from typing import Dict, Set
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from backend.app.services.storage_service import StorageService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем экземпляр сервиса хранения
storage = StorageService()

def has_company_markers(html: str) -> bool:
    """
    Проверяет наличие маркеров компании в HTML-контенте.
    """
    company_markers = [
        'ИНН',
        'ООО',
        'ОАО',
        'АО',
        'ИП',
        'реквизиты'
    ]
    
    return any(marker.lower() in html.lower() for marker in company_markers)

def looks_like_article(domain: str, html: str) -> bool:
    """
    Проверяет, похож ли контент на статью или информационный ресурс.
    """
    article_domains = ['wikipedia.org', 'wiki', 'blog', 'forum', 'news']
    return any(domain in domain.lower() for domain in article_domains)

def get_domain_from_url(url: str) -> str:
    """
    Извлекает домен из URL.
    """
    try:
        parsed_uri = urlparse(url)
        domain = parsed_uri.netloc
        return domain
    except Exception as e:
        logger.error(f"Error parsing URL {url}: {e}")
        return ""

def process_site(url: str, html: str, keyword: str) -> None:
    """
    Обрабатывает один сайт и сохраняет его в соответствующую категорию.
    """
    domain = get_domain_from_url(url)
    print(f"Обработка сайта: {domain}")
    
    # Сохраняем HTML-контент сайта
    html_path = storage.save_site_html(url, html)
    if not html_path:
        print(f"Не удалось сохранить HTML для сайта {domain}")
        return
    
    # Определяем категорию
    if has_company_markers(html):
        category = "suppliers"
        print(f"Сайт {domain} определён как suppliers")
    elif looks_like_article(domain, html):
        category = "others"
        print(f"Сайт {domain} определён как others")
    else:
        # Если не подходит ни под одну категорию, считаем поставщиком
        category = "suppliers"
        print(f"Сайт {domain} определён как suppliers (по умолчанию)")
    
    # Связываем сайт с ключевым словом и категорией
    if not storage.save_result_for_keyword(keyword, url, category):
        print(f"Не удалось сохранить результат для ключевого слова {keyword}")

def process_results(results: list) -> None:
    """Обрабатывает список результатов и сохраняет HTML-контент."""
    logger.info(f"Processing {len(results)} results")
    processed_domains = {}

    for result in results:
        try:
            if not isinstance(result, dict):
                logger.error(f"Invalid result format: {result}")
                continue

            url = result.get('url')
            html_content = result.get('html_content')

            if not url or not html_content:
                logger.error(f"Missing URL or HTML content in result: {result}")
                continue

            logger.info(f"Processing result: {url}")
            save_html_content(url, html_content, processed_domains)

        except Exception as e:
            logger.error(f"Error processing result: {e}")
            continue

    logger.info(f"Processed {len(processed_domains)} unique domains")

def save_html_content(url: str, html: str, processed_domains: Dict[str, str]) -> None:
    try:
        logger.info(f"Attempting to save content from URL: {url}")
        
        domain = get_domain_from_url(url)
        if not domain:
            logger.error(f"Could not extract domain from URL: {url}")
            return

        if domain in processed_domains:
            logger.info(f"Domain {domain} already processed, skipping")
            return

        # Получаем абсолютный путь к директории проекта
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        results_dir = os.path.join(base_dir, 'results')
        
        logger.info(f"Base directory: {base_dir}")
        logger.info(f"Results directory: {results_dir}")

        # Создаем директории если они не существуют
        os.makedirs(os.path.join(results_dir, 'suppliers'), exist_ok=True)
        os.makedirs(os.path.join(results_dir, 'others'), exist_ok=True)

        # Определяем категорию и путь для сохранения
        if has_company_markers(html):
            category_dir = 'suppliers'
            logger.info(f"Categorized as supplier: {domain}")
        else:
            category_dir = 'others'
            logger.info(f"Categorized as other: {domain}")

        file_path = os.path.join(results_dir, category_dir, f"{domain}.html")
        logger.info(f"Saving to file: {file_path}")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
            logger.info(f"Successfully saved content to {file_path}")

        processed_domains[domain] = category_dir
        logger.info(f"Added {domain} to processed domains")

    except Exception as e:
        logger.error(f"Error saving content for {url}: {e}")
        logger.error(f"Error details: {str(e)}")
        logger.error(f"Current working directory: {os.getcwd()}") 