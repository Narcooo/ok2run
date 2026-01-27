from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import declarative_base, sessionmaker

from agent_approval_gate.config import get_settings

Base = declarative_base()


def get_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
            return create_engine(
                settings.database_url,
                connect_args=connect_args,
                poolclass=StaticPool,
                future=True,
            )
    return create_engine(settings.database_url, connect_args=connect_args, future=True)


def get_session_local():
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


SessionLocal = get_session_local()


def init_db() -> None:
    from agent_approval_gate import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
