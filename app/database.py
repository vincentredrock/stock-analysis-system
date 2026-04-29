from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

# Build engine with dialect-specific options
def build_engine(database_url: str):
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.debug,
        )
    # PostgreSQL (and other standard drivers)
    engine = create_engine(
        database_url,
        pool_pre_ping=True,  # verify connections before using them
        echo=settings.debug,
    )
    if database_url.startswith("postgresql"):
        @event.listens_for(engine, "connect")
        def set_search_path(dbapi_connection, connection_record):
            with dbapi_connection.cursor() as cursor:
                cursor.execute("SET search_path TO public")
    return engine


engine = build_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
