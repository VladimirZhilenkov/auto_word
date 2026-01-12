"""
Database configuration management for local and remote database connections.

Supports:
- SQLite (local file)
- PostgreSQL (remote)
- MySQL/MariaDB (remote)
"""

import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
import sys


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    
    db_type: str = "sqlite"
    
    # SQLite settings
    sqlite_path: str = ""
    
    # Remote database settings
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    
    # Connection options
    ssl_enabled: bool = False
    ssl_ca_cert: str = ""
    connection_timeout: int = 30
    pool_size: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_connection_url(self) -> str:
        """
        Build SQLAlchemy connection URL based on configuration.
        
        Returns:
            Database connection URL string
        """
        if self.db_type == DatabaseType.SQLITE.value:
            return f"sqlite:///{self.sqlite_path}"
        
        elif self.db_type == DatabaseType.POSTGRESQL.value:
            # postgresql://user:password@host:port/database
            auth = f"{self.username}:{self.password}@" if self.username else ""
            return f"postgresql://{auth}{self.host}:{self.port}/{self.database}"
        
        elif self.db_type == DatabaseType.MYSQL.value:
            # mysql+pymysql://user:password@host:port/database
            auth = f"{self.username}:{self.password}@" if self.username else ""
            return f"mysql+pymysql://{auth}{self.host}:{self.port}/{self.database}"
        
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def get_engine_options(self) -> Dict[str, Any]:
        """
        Get SQLAlchemy engine options based on database type.
        
        Returns:
            Dictionary of engine options
        """
        options = {
            'echo': False,
            'pool_pre_ping': True,  # Test connections before use
        }
        
        if self.db_type == DatabaseType.SQLITE.value:
            options['connect_args'] = {'check_same_thread': False}
        else:
            # Remote database options
            options['pool_size'] = self.pool_size
            options['pool_recycle'] = 3600  # Recycle connections after 1 hour
            options['pool_timeout'] = self.connection_timeout
            
            if self.ssl_enabled and self.ssl_ca_cert:
                if self.db_type == DatabaseType.POSTGRESQL.value:
                    options['connect_args'] = {
                        'sslmode': 'require',
                        'sslrootcert': self.ssl_ca_cert
                    }
                elif self.db_type == DatabaseType.MYSQL.value:
                    options['connect_args'] = {
                        'ssl': {'ca': self.ssl_ca_cert}
                    }
        
        return options
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate the configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.db_type == DatabaseType.SQLITE.value:
            if not self.sqlite_path:
                return False, "SQLite database path is required"
            return True, ""
        
        # Remote database validation
        if not self.host:
            return False, "Database host is required"
        if not self.database:
            return False, "Database name is required"
        if self.port <= 0 or self.port > 65535:
            return False, "Invalid port number"
        
        return True, ""


def get_app_dir() -> Path:
    """Get application directory."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


class ConfigManager:
    """
    Manages database configuration persistence.
    """
    
    CONFIG_FILE = "db_config.json"
    
    def __init__(self):
        self.config_path = get_app_dir() / "data" / self.CONFIG_FILE
        self._config: Optional[DatabaseConfig] = None
    
    def load_config(self) -> DatabaseConfig:
        """
        Load configuration from file or return defaults.
        
        Returns:
            DatabaseConfig instance
        """
        if self._config is not None:
            return self._config
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._config = DatabaseConfig.from_dict(data)
            except Exception as e:
                print(f"Error loading config: {e}")
                self._config = self._get_default_config()
        else:
            self._config = self._get_default_config()
        
        return self._config
    
    def save_config(self, config: DatabaseConfig) -> bool:
        """
        Save configuration to file.
        
        Args:
            config: DatabaseConfig to save
            
        Returns:
            True if successful
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Don't save password in plain text - use placeholder
            data = config.to_dict()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self._config = config
            return True
        
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def _get_default_config(self) -> DatabaseConfig:
        """Get default SQLite configuration."""
        default_path = get_app_dir() / "data" / "database.db"
        return DatabaseConfig(
            db_type=DatabaseType.SQLITE.value,
            sqlite_path=str(default_path)
        )
    
    def test_connection(self, config: DatabaseConfig) -> tuple[bool, str]:
        """
        Test database connection.
        
        Args:
            config: Configuration to test
            
        Returns:
            Tuple of (success, message)
        """
        from sqlalchemy import create_engine, text
        
        # Validate config first
        valid, error = config.validate()
        if not valid:
            return False, error
        
        try:
            url = config.get_connection_url()
            options = config.get_engine_options()
            
            engine = create_engine(url, **options)
            
            with engine.connect() as conn:
                # Test query
                if config.db_type == DatabaseType.SQLITE.value:
                    conn.execute(text("SELECT 1"))
                elif config.db_type == DatabaseType.POSTGRESQL.value:
                    result = conn.execute(text("SELECT version()"))
                    version = result.scalar()
                    return True, f"Connected to PostgreSQL: {version[:50]}..."
                elif config.db_type == DatabaseType.MYSQL.value:
                    result = conn.execute(text("SELECT VERSION()"))
                    version = result.scalar()
                    return True, f"Connected to MySQL: {version}"
            
            return True, "Connection successful"
        
        except Exception as e:
            return False, f"Connection failed: {str(e)}"


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
