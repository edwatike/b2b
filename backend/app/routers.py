from fastapi import APIRouter
from app.routes.search import router as search_router
from app.routes.companies import router as companies_router

router = APIRouter()

router.include_router(search_router, prefix="/search", tags=["Search Suppliers"])
router.include_router(companies_router, tags=["Companies"])
