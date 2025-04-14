import json
import os
import logging
import traceback
from typing import Dict, List, Set, Optional
from pathlib import Path
from datetime import datetime
import aiofiles
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        """Initialize storage with base paths"""
        logger.debug("=== Инициализация Storage ===")
        
        self.base_dir = Path(os.getcwd()) / 'results'
        self.suppliers_dir = self.base_dir / 'suppliers'
        self.others_dir = self.base_dir / 'others'
        self.sites_dir = self.base_dir / 'sites'
        self.metadata_file = self.base_dir / 'metadata.json'
        
        logger.debug(f"Текущая рабочая директория: {os.getcwd()}")
        logger.debug(f"Базовая директория: {self.base_dir}")
        logger.debug(f"Директория поставщиков: {self.suppliers_dir}")
        logger.debug(f"Директория других: {self.others_dir}")
        logger.debug(f"Директория сайтов: {self.sites_dir}")
        logger.debug(f"Файл метаданных: {self.metadata_file}")
        
        # Создаем все необходимые директории и проверяем права доступа
        asyncio.create_task(self._ensure_directory_access())
        
        # Загружаем или создаем метаданные
        self.metadata = self._load_metadata()
        self.processed_domains = self._load_processed_domains()
        
        logger.info("Инициализация Storage завершена успешно")
        
    def _ensure_directories(self) -> None:
        """Ensure all necessary directories exist"""
        logger.debug("=== Создание необходимых директорий ===")
        
        directories = [
            self.base_dir,
            self.suppliers_dir,
            self.others_dir,
            self.sites_dir
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Директория создана/существует: {directory}")
                logger.debug(f"Права доступа: {oct(os.stat(directory).st_mode)}")
            except Exception as e:
                logger.error(f"Ошибка при создании директории {directory}: {e}")
                logger.error(traceback.format_exc())
    
    def _load_processed_domains(self) -> Dict:
        """Load record of processed domains"""
        logger.debug("=== Загрузка обработанных доменов ===")
        
        record_file = self.base_dir / 'processed_domains.json'
        logger.debug(f"Файл с обработанными доменами: {record_file}")
        
        if record_file.exists():
            try:
                with open(record_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Загружено {len(data)} обработанных доменов")
                logger.debug(f"Список доменов: {list(data.keys())}")
                return data
            except Exception as e:
                logger.error(f"Ошибка загрузки processed_domains.json: {e}")
                logger.error(traceback.format_exc())
        return {}
    
    async def _save_processed_domains(self) -> None:
        """Save record of processed domains"""
        logger.debug("=== Сохранение обработанных доменов ===")
        
        try:
            record_file = self.base_dir / 'processed_domains.json'
            logger.debug(f"Сохранение в файл: {record_file}")
            logger.debug(f"Количество доменов: {len(self.processed_domains)}")
            
            async with aiofiles.open(record_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.processed_domains, ensure_ascii=False, indent=2))
            
            logger.info(f"Сохранено {len(self.processed_domains)} обработанных доменов")
            logger.debug(f"Размер файла: {os.path.getsize(record_file)} байт")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения processed_domains.json: {e}")
            logger.error(traceback.format_exc())
    
    def _load_metadata(self) -> Dict:
        """Загружает метаданные из файла или создает новые."""
        logger.debug("=== Загрузка метаданных ===")
        
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info("Метаданные успешно загружены")
                logger.debug(f"Размер метаданных: {len(json.dumps(data))} байт")
                return data
            except Exception as e:
                logger.error(f"Ошибка загрузки metadata.json: {e}")
                logger.error(traceback.format_exc())
                return self._create_empty_metadata()
        return self._create_empty_metadata()
    
    def _create_empty_metadata(self) -> Dict:
        """Создает пустую структуру метаданных."""
        logger.debug("Создание новой структуры метаданных")
        return {
            "domains": {},  # domain -> {category, keywords}
            "keywords": {}  # keyword -> [domains]
        }
    
    async def save_site(self, domain: str, html: str, keyword: str, category: str) -> None:
        """
        Save site content to appropriate directory
        
        Args:
            domain: Site domain
            html: HTML content
            keyword: Search keyword
            category: Site category ('suppliers' or 'others')
        """
        logger.debug(f"\n=== Начало save_site для домена {domain} ===")
        logger.debug(f"Категория: {category}")
        logger.debug(f"Ключевое слово: {keyword}")
        logger.debug(f"Размер HTML: {len(html) if html else 0} байт")
        logger.debug(f"Первые 100 символов HTML: {html[:100] if html else ''}")

        # Проверка входных данных
        if not domain:
            logger.error("Ошибка: пустой домен")
            return
        if not html:
            logger.error(f"Ошибка: пустой HTML для домена {domain}")
            return
        if category not in ['suppliers', 'others']:
            logger.error(f"Ошибка: неверная категория {category} для домена {domain}")
            return

        try:
            # Проверка на повторную обработку домена
            if domain in self.processed_domains:
                logger.info(f"Домен {domain} уже был обработан ранее")
                logger.debug(f"Предыдущая обработка: {self.processed_domains[domain]}")
                return

            # Создание имени файла с меткой времени
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{domain.replace('.', '_')}_{timestamp}.html"
            
            # Определение целевой директории
            target_dir = self.suppliers_dir if category == 'suppliers' else self.others_dir
            file_path = target_dir / filename

            logger.debug(f"Подготовка к сохранению:")
            logger.debug(f"- Метка времени: {timestamp}")
            logger.debug(f"- Имя файла: {filename}")
            logger.debug(f"- Целевая директория: {target_dir}")
            logger.debug(f"- Полный путь к файлу: {file_path}")
            
            # Проверка прав доступа к директории
            if not await self._check_directory_permissions(target_dir):
                logger.error(f"Недостаточно прав для сохранения в директорию {target_dir}")
                return

            # Сохранение HTML контента
            try:
                logger.debug(f"Начало записи HTML в файл {file_path}...")
                
                # Проверяем существование директории
                if not target_dir.exists():
                    logger.warning(f"Директория {target_dir} не существует, создаём...")
                    target_dir.mkdir(parents=True, exist_ok=True)
                
                # Проверяем права на запись
                if not os.access(target_dir, os.W_OK):
                    logger.error(f"Нет прав на запись в директорию {target_dir}")
                    return
                
                async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                    await f.write(html)
                
                # Проверка сохранённого файла
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Файл {file_path} не был создан")
                
                file_size = os.path.getsize(file_path)
                logger.info(f"HTML успешно сохранён, размер файла: {file_size} байт")
                
            except Exception as e:
                logger.error(f"Ошибка при сохранении HTML в файл {file_path}: {e}")
                logger.error(traceback.format_exc())
                raise

            # Обновление processed_domains
            try:
                logger.debug("Обновление записи обработанных доменов...")
                self.processed_domains[domain] = {
                    'category': category,
                    'keyword': keyword,
                    'timestamp': timestamp,
                    'filename': filename,
                    'file_size': file_size,
                    'file_path': str(file_path)
                }
                await self._save_processed_domains()
                logger.debug("Запись обработанных доменов обновлена")
                
            except Exception as e:
                logger.error(f"Ошибка при обновлении записи обработанных доменов: {e}")
                logger.error(traceback.format_exc())
                # Удаляем файл, если не удалось обновить метаданные
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Файл {file_path} удален из-за ошибки")
                raise

            # Обновление метаданных
            try:
                logger.debug("Обновление метаданных...")
                if domain not in self.metadata["domains"]:
                    self.metadata["domains"][domain] = {"category": category, "keywords": []}
                if keyword not in self.metadata["domains"][domain]["keywords"]:
                    self.metadata["domains"][domain]["keywords"].append(keyword)
                
                if keyword not in self.metadata["keywords"]:
                    self.metadata["keywords"][keyword] = []
                if domain not in self.metadata["keywords"][keyword]:
                    self.metadata["keywords"][keyword].append(domain)
                
                # Сохранение метаданных
                async with aiofiles.open(self.metadata_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(self.metadata, ensure_ascii=False, indent=2))
                logger.debug("Метаданные успешно обновлены")
                
            except Exception as e:
                logger.error(f"Ошибка при обновлении метаданных: {e}")
                logger.error(traceback.format_exc())
                # Удаляем файл и запись из processed_domains при ошибке
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Файл {file_path} удален из-за ошибки")
                if domain in self.processed_domains:
                    del self.processed_domains[domain]
                    logger.debug(f"Домен {domain} удален из processed_domains из-за ошибки")
                raise

            logger.info(f"=== Сайт {domain} успешно сохранён в категорию {category} ===")

        except Exception as e:
            logger.error(f"Критическая ошибка при сохранении сайта {domain}: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def get_sites_by_keyword(self, keyword: str) -> List[str]:
        """Возвращает список доменов для заданного ключевого слова."""
        return [domain for domain, info in self.processed_domains.items() 
                if info['keyword'] == keyword]
    
    def get_site_info(self, domain: str) -> Optional[Dict]:
        """Возвращает информацию о сайте по домену."""
        return self.processed_domains.get(domain)
    
    async def get_site_html(self, domain: str) -> Optional[str]:
        """Возвращает HTML-контент сайта по домену."""
        if domain not in self.processed_domains:
            return None
            
        info = self.processed_domains[domain]
        file_path = os.path.join(self.base_dir, info['category'], info['filename'])
        
        if os.path.exists(file_path):
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    return await f.read()
            except Exception as e:
                logger.error(f"Error reading HTML for {domain}: {e}")
        return None
    
    def get_all_keywords(self) -> List[str]:
        """Возвращает список всех ключевых слов."""
        return list(set(info['keyword'] for info in self.processed_domains.values()))
    
    def get_sites_by_category(self, category: str) -> List[str]:
        """Возвращает список доменов в заданной категории."""
        return [domain for domain, info in self.processed_domains.items()
                if info['category'] == category]

    async def _check_directory_permissions(self, directory: Path) -> bool:
        """
        Проверяет права доступа к директории.
        
        Args:
            directory: Путь к директории
            
        Returns:
            bool: True если есть права на чтение и запись, False в противном случае
        """
        logger.debug(f"=== Проверка прав доступа к директории {directory} ===")
        
        try:
            # Проверяем существование директории
            if not directory.exists():
                logger.warning(f"Директория {directory} не существует, создаём...")
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Директория создана: {directory}")
            
            # Проверяем права на чтение
            if not os.access(directory, os.R_OK):
                logger.error(f"Нет прав на чтение директории {directory}")
                return False
                
            # Проверяем права на запись
            if not os.access(directory, os.W_OK):
                logger.error(f"Нет прав на запись в директорию {directory}")
                return False
                
            # Пробуем создать тестовый файл
            test_file = directory / '.test_permissions'
            try:
                logger.debug(f"Создание тестового файла: {test_file}")
                async with aiofiles.open(test_file, 'w') as f:
                    await f.write('test')
                os.remove(test_file)
                logger.debug(f"Тестовый файл успешно создан и удален")
                logger.info(f"Проверка прав доступа к {directory}: OK")
                return True
            except Exception as e:
                logger.error(f"Ошибка при создании тестового файла в {directory}: {e}")
                logger.error(traceback.format_exc())
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при проверке прав доступа к {directory}: {e}")
            logger.error(traceback.format_exc())
            return False
            
    async def _ensure_directory_access(self) -> bool:
        """
        Проверяет права доступа ко всем необходимым директориям.
        
        Returns:
            bool: True если все проверки пройдены, False в противном случае
        """
        directories = [
            self.base_dir,
            self.suppliers_dir,
            self.others_dir,
            self.sites_dir
        ]
        
        logger.info("=== Проверка прав доступа к директориям ===")
        
        for directory in directories:
            if not await self._check_directory_permissions(directory):
                logger.error(f"Ошибка доступа к директории {directory}")
                return False
                
        logger.info("Все директории доступны для чтения и записи")
        return True
