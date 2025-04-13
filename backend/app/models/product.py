from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    price: Decimal = Field(default=0.0)
    quantity: int = Field(default=0) 