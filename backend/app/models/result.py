from sqlmodel import SQLModel
from typing import Optional

class ResultItem(SQLModel):
    name: str
    email: str
    city: Optional[str]
    site: Optional[str]