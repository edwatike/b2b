import logging
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Database URL from environment variable or default
DATABASE_URL = "postgresql+asyncpg://b2b_user:b2b_pass@db:5432/b2b_db"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create async session
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Initialize database."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)
        
async def get_session() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        yield session 