from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Index
from typing import Optional


class SearchResult(SQLModel, table=True):
    """
    Модель для хранения результатов поиска
    
    Индексы:
    - query: для быстрого поиска по запросу
    - result_url: для проверки дубликатов
    - title: для поиска по заголовкам
    - created_at: для TTL и сортировки
    - (query, result_url): составной индекс для уникальности
    """
    __tablename__ = "search_results"
    __table_args__ = (
        Index("ix_search_results_query", "query"),
        Index("ix_search_results_url", "result_url"),
        Index("ix_search_results_title", "title"),
        Index("ix_search_results_created_at", "created_at"),
        Index("ix_search_results_query_url", "query", "result_url", unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    query: str = Field(max_length=255)
    result_url: str = Field(max_length=2048)
    title: Optional[str] = Field(default=None, max_length=512)
    snippet: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Дата создания записи"
    )

    @property
    def is_expired(self) -> bool:
        """
        Проверяет, истек ли срок хранения результата (30 дней)
        """
        ttl = timedelta(days=30)
        return datetime.utcnow() - self.created_at > ttl

    def __repr__(self):
        return f"<SearchResult(id={self.id}, query='{self.query}', url='{self.result_url}')>" 