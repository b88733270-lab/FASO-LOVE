"""Moteur et fabrique de sessions SQLAlchemy (async)."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

engine: AsyncEngine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
