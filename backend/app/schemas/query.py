from pydantic import BaseModel
from typing import List

class SearchRequest(BaseModel):
    query: str

class ResultItem(BaseModel):
    company: str
    website: str
    email: str
    product_found: bool

class SearchResponse(BaseModel):
    results: List[ResultItem]
