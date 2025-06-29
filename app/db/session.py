from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


class DBSessionManager:

    def __init__(self) -> None:
        self.engine = create_engine(
            settings.database.database_url,
            future=True,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle,
            pool_pre_ping=settings.database.pool_pre_ping,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,
        )

    def get_session(self) -> Session:
        session: Session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()


db_manager = DBSessionManager()


def get_db() -> Session:
    # Returns a single session for dependency injection (using next() to
    # obtain first yield)
    return next(db_manager.get_session())
