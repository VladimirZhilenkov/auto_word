"""
Backup Manager Service for database and document backups.

Provides functionality to:
- Create timestamped backup copies of the database
- Manage backup files (list, delete, restore)
- Auto-backup before major operations
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from ..database.connection import DatabaseSession


class BackupManager:
    """
    Manage database backups with timestamps.
    """
    
    def __init__(self, db_path: Path = None, backup_dir: Path = None):
        """
        Initialize backup manager.
        
        Args:
            db_path: Path to the database file
            backup_dir: Directory to store backups (default: data/backups)
        """
        # Default paths
        app_root = Path(__file__).parent.parent.parent
        self.db_path = db_path or (app_root / "data" / "database.db")
        self.backup_dir = backup_dir or (app_root / "data" / "backups")
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, description: str = "") -> Optional[str]:
        """
        Create a timestamped backup of the database.
        
        Args:
            description: Optional description for the backup
        
        Returns:
            Path to created backup file, or None if failed
        """
        if not self.db_path.exists():
            return None
        
        try:
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Build backup filename
            backup_name = f"database_{timestamp}.db"
            if description:
                # Clean description for filename
                clean_desc = "".join(c if c.isalnum() or c in "_- " else "" 
                                    for c in description).strip().replace(" ", "_")
                backup_name = f"database_{timestamp}_{clean_desc}.db"
            
            backup_path = self.backup_dir / backup_name
            
            # Copy database file
            shutil.copy2(str(self.db_path), str(backup_path))
            
            # Create metadata file
            self._create_backup_metadata(backup_path, description)
            
            return str(backup_path)
        
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None
    
    def _create_backup_metadata(self, backup_path: Path, description: str = ""):
        """Create metadata file for backup."""
        metadata_path = backup_path.with_suffix('.meta')
        
        metadata = {
            'created': datetime.now().isoformat(),
            'original_size': self.db_path.stat().st_size if self.db_path.exists() else 0,
            'backup_size': backup_path.stat().st_size,
            'description': description
        }
        
        # Write metadata as simple text file
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(f"Created: {metadata['created']}\n")
            f.write(f"Description: {metadata['description']}\n")
            f.write(f"Original Size: {metadata['original_size']} bytes\n")
            f.write(f"Backup Size: {metadata['backup_size']} bytes\n")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        try:
            for backup_file in sorted(self.backup_dir.glob("database_*.db"), reverse=True):
                backup_info = {
                    'path': str(backup_file),
                    'name': backup_file.name,
                    'size': backup_file.stat().st_size,
                    'created': datetime.fromtimestamp(backup_file.stat().st_mtime),
                    'description': self._read_backup_description(backup_file)
                }
                backups.append(backup_info)
        
        except Exception as e:
            print(f"Error listing backups: {e}")
        
        return backups
    
    def _read_backup_description(self, backup_path: Path) -> str:
        """Read description from backup metadata file."""
        try:
            metadata_path = backup_path.with_suffix('.meta')
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('Description:'):
                            return line.split(':', 1)[1].strip()
        except:
            pass
        return ""
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file to restore
        
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_path)
            
            if not backup_path.exists():
                print(f"Backup file not found: {backup_path}")
                return False
            
            # Create a safety backup of current database
            current_backup = self.db_path.with_stem(
                f"{self.db_path.stem}_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            if self.db_path.exists():
                shutil.copy2(str(self.db_path), str(current_backup))
            
            # Restore from backup
            shutil.copy2(str(backup_path), str(self.db_path))
            
            # Create restore metadata
            metadata_path = self.db_path.with_suffix('.meta')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(f"Restored from: {backup_path.name}\n")
                f.write(f"Restored at: {datetime.now().isoformat()}\n")
            
            return True
        
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
    
    def delete_backup(self, backup_path: str) -> bool:
        """
        Delete a backup file.
        
        Args:
            backup_path: Path to backup file to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_path)
            
            if backup_path.exists():
                backup_path.unlink()
            
            # Delete metadata file if exists
            metadata_path = backup_path.with_suffix('.meta')
            if metadata_path.exists():
                metadata_path.unlink()
            
            return True
        
        except Exception as e:
            print(f"Error deleting backup: {e}")
            return False
    
    def auto_backup(self, description: str = "Auto-backup") -> Optional[str]:
        """
        Create automatic backup (typically before major operations).
        
        Args:
            description: Description for auto-backup
        
        Returns:
            Path to created backup file
        """
        # Limit number of auto-backups to last 10
        auto_backups = sorted(
            self.backup_dir.glob("database_*auto*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Delete oldest if we have more than 10
        if len(auto_backups) > 10:
            for old_backup in auto_backups[10:]:
                try:
                    self.delete_backup(str(old_backup))
                except:
                    pass
        
        return self.create_backup(description)
    
    def get_backup_dir(self) -> Path:
        """Get the backup directory path."""
        return self.backup_dir
    
    def get_backup_size_mb(self, backup_path: str) -> float:
        """Get size of backup in MB."""
        try:
            return Path(backup_path).stat().st_size / (1024 * 1024)
        except:
            return 0.0
