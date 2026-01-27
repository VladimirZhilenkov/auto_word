#!/usr/bin/env python3
"""
Migration script to add training_duration field to programs table.
"""

import sqlite3
from pathlib import Path

def migrate():
    """Add training_duration column to programs table."""
    db_path = Path("data/database.db")
    
    if not db_path.exists():
        print("Database not found. It will be created on first run.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(programs)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "training_duration" in columns:
        print("✓ Column 'training_duration' already exists")
    else:
        cursor.execute("""
            ALTER TABLE programs 
            ADD COLUMN training_duration VARCHAR(100)
        """)
        conn.commit()
        print("✓ Added column 'training_duration' to programs table")
    
    conn.close()
    print("Migration completed!")

if __name__ == "__main__":
    migrate()
