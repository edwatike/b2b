from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, Index
from typing import Optional


class SearchResult(SQLModel, table=True):
    """
    Модель для хранения результатов поиска
    """
    __tablename__ = "search_results"
    __table_args__ = (
        {"extend_existing": True}
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    domain: str
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    region: Optional[str] = None
    category: Optional[str] = None
    query: str = Field(max_length=255, index=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    result_url: str = Field(max_length=2048)
    title: Optional[str] = Field(default=None, max_length=512)
    snippet: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """
        Проверяет, истек ли срок хранения результата (30 дней)
        """
        ttl = timedelta(days=30)
        return datetime.utcnow() - self.created_at > ttl

    def __repr__(self):
        return f"<SearchResult(id={self.id}, query='{self.query}', url='{self.result_url}')>" 