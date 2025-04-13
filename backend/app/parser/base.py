from abc import ABC, abstractmethod
from typing import List
from app.models.result import ResultItem

class BaseParser(ABC):
    @abstractmethod
    async def parse(self, keyword: str) -> List[ResultItem]:
        pass