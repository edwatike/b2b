from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime
from pydantic import HttpUrl

class SearchResult(SQLModel, table=False):
    """
    Модель данных для результатов поиска в парсере
    """
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    position: int = 0
    source: str = "google"

class SearchRequest(SQLModel):
    """
    Модель данных для запроса поиска
    """
    query: str
    region: Optional[str] = None
    category: Optional[str] = None
    limit: int = 30

class SearchResponse(SQLModel):
    """
    Модель данных для ответа на запрос поиска
    """
    results: List[SearchResult]
    total: int
    cached: int
    new: int 