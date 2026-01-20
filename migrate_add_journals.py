#!/usr/bin/env python3
"""
Database migration script for adding OrderJournal table.
Creates order_journal table if it doesn't exist in the database.
Safe to run multiple times - checks for existing table first.
"""

import sqlite3
import sys
from pathlib import Path


def get_db_path():
    """Get the database path."""
    app_dir = Path(__file__).parent
    return app_dir / "data" / "database.db"


def table_exists(cursor, table_name):
    """Check if a table exists in the database."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def migrate_add_order_journal():
    """Add order_journal table to the database."""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Run the application first to create the database.")
        return False

    print(f"Migrating database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if order_journal table already exists
        if table_exists(cursor, "order_journal"):
            print("✅ Table 'order_journal' already exists. No migration needed.")
            conn.close()
            return True

        # Create order_journal table
        create_table_sql = """
        CREATE TABLE order_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_type VARCHAR(50) NOT NULL,
            order_number INTEGER NOT NULL,
            order_date DATE NOT NULL,
            title TEXT NOT NULL,
            executor VARCHAR(255) NOT NULL,
            program_id INTEGER,
            program_name TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            document_path VARCHAR(500),
            FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE SET NULL,
            CONSTRAINT uq_order_journal_type_number UNIQUE (journal_type, order_number)
        )
        """

        cursor.execute(create_table_sql)

        # Create indexes
        cursor.execute(
            "CREATE INDEX ix_order_journal_type_number ON order_journal(journal_type, order_number)"
        )
        cursor.execute(
            "CREATE INDEX ix_order_journal_date ON order_journal(order_date)"
        )

        conn.commit()
        print("\n✅ Created table 'order_journal' with indexes")

        # Optional: migrate data from DocumentRegister if needed
        # This part can import existing orders if you want to preserve history
        if table_exists(cursor, "document_register"):
            print("\n📋 Checking DocumentRegister for existing orders...")
            cursor.execute(
                """
                SELECT document_type, COUNT(*)
                FROM document_register
                WHERE document_type IN ('enrollment', 'admission', 'graduation')
                GROUP BY document_type
                """
            )
            existing_orders = cursor.fetchall()
            if existing_orders:
                print("   Existing orders found in DocumentRegister:")
                for doc_type, count in existing_orders:
                    print(f"     - {doc_type}: {count} records")
                print("   Note: Automatic migration not performed.")
                print("   You can manually copy records if needed using custom SQL.")
            else:
                print("   No order records found in DocumentRegister.")

        conn.close()

        print("\n✅ Migration completed successfully!")
        print("   Order journal system is now ready to use.")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = migrate_add_order_journal()
    sys.exit(0 if success else 1)
