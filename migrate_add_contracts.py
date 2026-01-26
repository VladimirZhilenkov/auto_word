#!/usr/bin/env python3
"""
Adds contract_journal table to existing SQLite database.
Safe for repeated runs.
"""

import sqlite3
import sys
from pathlib import Path


def get_db_path() -> Path:
    return Path(__file__).parent / "data" / "database.db"


def table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def migrate_add_contracts() -> bool:
    db_path = get_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Run the application once to create the database.")
        return False

    print(f"Migrating database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if table_exists(cursor, "contract_journal"):
            print("✅ Table 'contract_journal' already exists. Nothing to do.")
            conn.close()
            return True

        cursor.execute(
            """
            CREATE TABLE contract_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_number INTEGER NOT NULL UNIQUE,
                contract_date DATE NOT NULL,
                listener_id INTEGER,
                program_id INTEGER,
                listener_full_name VARCHAR(255),
                program_name VARCHAR(500),
                contract_sum VARCHAR(100),
                payment_type VARCHAR(100),
                notes TEXT,
                document_path VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(listener_id) REFERENCES listeners(id) ON DELETE SET NULL,
                FOREIGN KEY(program_id) REFERENCES programs(id) ON DELETE SET NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX ix_contract_journal_date ON contract_journal(contract_date)"
        )

        conn.commit()
        conn.close()
        print("✅ Migration completed: contract_journal created")
        return True
    except Exception as exc:
        print(f"❌ Migration failed: {exc}")
        return False


if __name__ == "__main__":
    success = migrate_add_contracts()
    sys.exit(0 if success else 1)
