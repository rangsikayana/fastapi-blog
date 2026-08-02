from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

engine = create_engine(  # Conn to the DB
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False
    },  # Disables FastAPI multi threads default specifically for SQLite
)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)  # False are set to gain control over commits


class Base(DeclarativeBase):  # Used for creating tables
    pass


def get_db():  # Provides sessions to routes
    with SessionLocal() as db:  # "with" ensures clean up after HTTP response is sent
        yield db  # Uses yield instead of return to pause exec & passes DB sess to route
