from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

engine = create_async_engine(  # Conn to the DB
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False
    },  # Disables FastAPI multi threads default specifically for SQLite
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)  # False prevents lazy loading expired obj after a commit in async


class Base(DeclarativeBase):  # Used for creating tables
    pass


async def get_db():  # Provides sessions to routes
    async with (
        AsyncSessionLocal() as session
    ):  # "with" ensures clean up after HTTP response is sent
        yield session  # Uses yield instead of return to pause exec & passes DB sess to route
