"""
Database connection management for SQLite with SQLAlchemy 2.0+
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


# Default database path
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATABASE_PATH = DATA_DIR / "database.db"


def get_database_url(db_path: Path = None) -> str:
    """Get SQLite database URL."""
    path = db_path or DATABASE_PATH
    return f"sqlite:///{path}"


def get_engine(db_path: Path = None) -> Engine:
    """Create and return SQLAlchemy engine."""
    url = get_database_url(db_path)
    engine = create_engine(
        url,
        echo=False,  # Set to True for SQL debugging
        connect_args={"check_same_thread": False}  # Required for SQLite
    )
    return engine


# Enable foreign key support for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys in SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Global engine and session factory
_engine = None
_SessionFactory = None


def init_database(db_path: Path = None) -> Engine:
    """
    Initialize database: create engine, tables, and session factory.
    
    Args:
        db_path: Optional custom database path
        
    Returns:
        SQLAlchemy Engine instance
    """
    global _engine, _SessionFactory
    
    # Ensure data directory exists
    path = db_path or DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create engine
    _engine = get_engine(path)
    
    # Create all tables
    Base.metadata.create_all(_engine)
    
    # Create session factory
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    
    return _engine


def get_session() -> Session:
    """Get a new database session."""
    global _SessionFactory
    
    if _SessionFactory is None:
        init_database()
    
    return _SessionFactory()


@contextmanager
def DatabaseSession() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Usage:
        with DatabaseSession() as session:
            session.query(Model).all()
            session.add(instance)
            session.commit()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DatabaseManager:
    """
    Database manager for handling connections and operations.
    """
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DATABASE_PATH
        self.engine = None
        self.session_factory = None
    
    def initialize(self):
        """Initialize the database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = get_engine(self.db_path)
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
    
    def get_session(self) -> Session:
        """Get a new session."""
        if self.session_factory is None:
            self.initialize()
        return self.session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def backup_database(self, backup_path: Path) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path for the backup file
            
        Returns:
            True if successful
        """
        import shutil
        try:
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
