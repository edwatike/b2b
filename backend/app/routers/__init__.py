from fastapi import APIRouter
from . import companies, search, products  # добавляем products
from .router_parser import router as parser_router

router = APIRouter()
router.include_router(companies.router, prefix="/companies", tags=["companies"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(products.router, prefix="/products", tags=["products"])
router.include_router(parser_router, prefix="/parser", tags=["parser"])

