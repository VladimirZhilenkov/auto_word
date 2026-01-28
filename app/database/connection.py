"""
Database connection management for SQLite and remote databases with SQLAlchemy 2.0+

Supports:
- SQLite (local file)
- PostgreSQL (remote)
- MySQL/MariaDB (remote)
"""

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base
from .config import DatabaseConfig, DatabaseType, get_config_manager


def get_app_dir() -> Path:
    """Get application directory (works for both dev and compiled)."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # Use directory where exe is located
        return Path(sys.executable).parent
    else:
        # Running in development
        return Path(__file__).parent.parent.parent


# Default database path
DATA_DIR = get_app_dir() / "data"
DATABASE_PATH = DATA_DIR / "database.db"

# Current database configuration
_current_config: Optional[DatabaseConfig] = None


def get_database_url(db_path: Path = None) -> str:
    """Get SQLite database URL (legacy support)."""
    path = db_path or DATABASE_PATH
    return f"sqlite:///{path}"


def get_engine_from_config(config: DatabaseConfig) -> Engine:
    """
    Create SQLAlchemy engine from configuration.
    
    Args:
        config: Database configuration
        
    Returns:
        SQLAlchemy Engine instance
    """
    url = config.get_connection_url()
    options = config.get_engine_options()
    
    engine = create_engine(url, **options)
    return engine


def get_engine(db_path: Path = None) -> Engine:
    """Create and return SQLAlchemy engine (legacy support for SQLite)."""
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
    # Check if this is SQLite connection
    if hasattr(dbapi_connection, 'execute'):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:
            # Not SQLite, ignore
            pass


# Global engine and session factory
_engine = None
_SessionFactory = None


def _run_migrations(engine: Engine):
    """
    Run automatic database migrations to add missing columns.
    This ensures smooth updates from older versions.
    """
    # Define all columns that should exist in each table
    # Format: (table_name, column_name, column_type)
    migrations = [
        # Programs table columns
        ("programs", "training_duration", "VARCHAR(100)"),
        ("programs", "program_short_name", "VARCHAR(255)"),
        ("programs", "training_basis", "VARCHAR(100)"),
        ("programs", "training_period", "VARCHAR(100)"),
        ("programs", "program_volume", "VARCHAR(100)"),
        ("programs", "education_form", "VARCHAR(50)"),
        ("programs", "education_format", "TEXT"),
        ("programs", "listener_category", "VARCHAR(255)"),
        ("programs", "expulsion_date", "DATE"),
        
        # Listeners table columns
        ("listeners", "gender", "VARCHAR(1) DEFAULT 'M'"),
        ("listeners", "education", "TEXT"),
        ("listeners", "birth_date", "DATE"),
        ("listeners", "mobile_phone", "VARCHAR(50)"),
        ("listeners", "work_phone", "VARCHAR(50)"),
        ("listeners", "email", "VARCHAR(255)"),
        ("listeners", "passport_series_number", "VARCHAR(20)"),
        ("listeners", "passport_issue_date", "DATE"),
        ("listeners", "passport_issued_by", "VARCHAR(500)"),
        ("listeners", "passport_department_code", "VARCHAR(20)"),
        ("listeners", "registration_address", "VARCHAR(500)"),
        ("listeners", "actual_address", "VARCHAR(500)"),
        ("listeners", "snils", "VARCHAR(20)"),
        ("listeners", "inn", "VARCHAR(20)"),
        ("listeners", "personal_data_consent", "INTEGER DEFAULT 0"),
        
        # ProgramListener table columns
        ("program_listeners", "order_number", "INTEGER"),
        ("program_listeners", "enrollment_date", "DATE"),
    ]
    
    with engine.connect() as conn:
        for table_name, column_name, column_type in migrations:
            try:
                # Check if column exists
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                existing_columns = [row[1] for row in result.fetchall()]
                
                if column_name not in existing_columns:
                    # Add missing column
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
                    conn.commit()
                    print(f"Migration: added column {table_name}.{column_name}")
            except Exception as e:
                # Silently ignore errors (column might already exist or table doesn't exist yet)
                pass


def init_database(db_path: Path = None, config: DatabaseConfig = None) -> Engine:
    """
    Initialize database: create engine, tables, and session factory.
    
    Args:
        db_path: Optional custom database path (for SQLite, legacy)
        config: Optional DatabaseConfig for remote databases
        
    Returns:
        SQLAlchemy Engine instance
    """
    global _engine, _SessionFactory, _current_config
    
    if config is not None:
        # Use provided configuration
        _current_config = config
        _engine = get_engine_from_config(config)
        
        # For SQLite, ensure directory exists
        if config.db_type == DatabaseType.SQLITE.value:
            Path(config.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    else:
        # Legacy SQLite initialization
        path = db_path or DATABASE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        _engine = get_engine(path)
        
        # Create default config
        _current_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE.value,
            sqlite_path=str(path)
        )
    
    # Create all tables
    Base.metadata.create_all(_engine)
    
    # Run migrations for existing databases (add missing columns)
    _run_migrations(_engine)
    
    # Create session factory
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    
    return _engine


def init_from_config() -> Engine:
    """
    Initialize database from saved configuration.
    
    Returns:
        SQLAlchemy Engine instance
    """
    config_manager = get_config_manager()
    config = config_manager.load_config()
    return init_database(config=config)


def get_current_config() -> Optional[DatabaseConfig]:
    """Get current database configuration."""
    global _current_config
    return _current_config


def switch_database(config: DatabaseConfig) -> tuple[bool, str]:
    """
    Switch to a different database connection.
    
    Args:
        config: New database configuration
        
    Returns:
        Tuple of (success, message)
    """
    global _engine, _SessionFactory, _current_config
    
    # Validate config
    valid, error = config.validate()
    if not valid:
        return False, error
    
    try:
        # Close existing connections
        if _engine is not None:
            _engine.dispose()
        
        # Initialize new connection
        init_database(config=config)
        
        # Save configuration
        config_manager = get_config_manager()
        config_manager.save_config(config)
        
        return True, "Database switched successfully"
    
    except Exception as e:
        return False, f"Failed to switch database: {str(e)}"


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
