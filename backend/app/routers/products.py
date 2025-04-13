from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db import async_session
from app.models.product import Product

router = APIRouter()

# Получаем сессию БД
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

# Поиск продуктов по названию
@router.get("/products/search")
async def search_products(query: str, session: AsyncSession = Depends(get_session)):
    statement = select(Product).where(Product.name.contains(query))
    results = await session.execute(statement)
    products = results.scalars().all()
    return {
        "query": query,
        "results": products
    } 