"""Database module for Document Generator."""

from .connection import (
    DatabaseSession, get_engine, init_database, 
    init_from_config, switch_database, get_current_config
)
from .models import Base, Listener, Program, ProgramListener, DocumentRegister
from .config import DatabaseConfig, DatabaseType, ConfigManager, get_config_manager

__all__ = [
    'DatabaseSession',
    'get_engine',
    'init_database',
    'init_from_config',
    'switch_database',
    'get_current_config',
    'Base',
    'Listener',
    'Program',
    'ProgramListener',
    'DocumentRegister',
    'DatabaseConfig',
    'DatabaseType',
    'ConfigManager',
    'get_config_manager',
]
