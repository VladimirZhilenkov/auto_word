#!/usr/bin/env python3
"""
Database migration script for adding new listener fields.
Run this once after updating to add new columns to the existing database.
"""

import sqlite3
import sys
from pathlib import Path


def get_db_path():
    """Get the database path."""
    app_dir = Path(__file__).parent
    return app_dir / "data" / "database.db"


def get_existing_columns(cursor, table_name):
    """Get list of existing columns in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def migrate_listeners_table():
    """Add new columns to the listeners table."""
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Run the application first to create the database.")
        return False
    
    print(f"Migrating database: {db_path}")
    
    # New columns to add
    new_columns = [
        ("birth_date", "DATE"),
        ("mobile_phone", "VARCHAR(50)"),
        ("work_phone", "VARCHAR(50)"),
        ("email", "VARCHAR(100)"),
        ("passport_series_number", "VARCHAR(20)"),
        ("passport_issue_date", "DATE"),
        ("passport_issued_by", "VARCHAR(255)"),
        ("passport_department_code", "VARCHAR(10)"),
        ("registration_address", "TEXT"),
        ("actual_address", "TEXT"),
        ("snils", "VARCHAR(20)"),
        ("inn", "VARCHAR(15)"),
        ("personal_data_consent", "BOOLEAN DEFAULT 0"),
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get existing columns
        existing = get_existing_columns(cursor, "listeners")
        print(f"Existing columns: {existing}")
        
        # Add new columns
        added = []
        skipped = []
        
        for col_name, col_type in new_columns:
            if col_name in existing:
                skipped.append(col_name)
            else:
                try:
                    cursor.execute(f"ALTER TABLE listeners ADD COLUMN {col_name} {col_type}")
                    added.append(col_name)
                except sqlite3.OperationalError as e:
                    print(f"Error adding column {col_name}: {e}")
        
        conn.commit()
        conn.close()
        
        if added:
            print(f"\n✅ Added columns: {', '.join(added)}")
        if skipped:
            print(f"⏭️  Skipped (already exist): {', '.join(skipped)}")
        
        if not added and skipped:
            print("\n✅ Database is already up to date!")
        else:
            print("\n✅ Migration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = migrate_listeners_table()
    sys.exit(0 if success else 1)
