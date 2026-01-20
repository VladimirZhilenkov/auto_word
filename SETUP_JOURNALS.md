# Quick Setup Guide — Order Journal System

## Prerequisites
✓ Application already installed and running
✓ Python 3.8+ with PyQt5, SQLAlchemy, openpyxl

## Installation Steps

### 1. Run Migration (One-time)

```bash
cd /Volumes/New/auto_word
python migrate_add_journals.py
```

**Expected output:**
```
Migrating database: /Volumes/New/auto_word/data/database.db
✅ Created table 'order_journal' with indexes
✅ Migration completed successfully!
```

### 2. Restart Application

```bash
python main.py
```

### 3. Verify Installation

1. Open the application
2. Check for new **"Журналы"** tab
3. Check menu **"Файл" → "Экспорт журналов"**

## First Use

### Test Order Creation with Journal

1. **Create an order:**
   - Menu: "Файл" → "Создать приказ" (or Ctrl+Shift+G)
   - Select order type: "О зачислении"
   - Notice: "Следующий номер в журнале: №1"
   - Fill in program name, dates, select listeners
   - Click "Сгенерировать приказ"

2. **Verify registration:**
   - Look for message: "✓ Зарегистрирован в журнале под номером: 1"
   - Switch to "Журналы" tab
   - See the newly created entry

### Test Manual Entry

1. Go to "Журналы" tab
2. Click "Добавить запись вручную"
3. Fill in:
   - Type: "О допуске к аттестации"
   - Number: 1 (auto-suggested)
   - Date: today
   - Title: "Test manual entry"
   - Executor: "Test User"
4. Click "Сохранить"
5. Entry appears in table

### Test Export

1. On "Журналы" tab
2. Select type and date range
3. Click "Экспорт в Excel"
4. Choose save location
5. Open Excel file to verify format

## Files Created

```
/Volumes/New/auto_word/
├── app/
│   ├── database/
│   │   └── models.py              # OrderJournal model added
│   ├── services/
│   │   └── order_journal_service.py   # NEW
│   └── ui/
│       ├── journals_tab.py        # NEW
│       ├── dialogs/
│       │   └── journal_entry_dialog.py  # NEW
│       ├── dialogs/order_dialog.py    # Modified
│       └── main_window.py         # Modified
├── migrate_add_journals.py        # NEW - run once
├── JOURNAL_SYSTEM_IMPLEMENTATION.md   # Documentation
└── РУКОВОДСТВО_ЖУРНАЛЫ.md         # User guide (Russian)
```

## Database Changes

**New table:** `order_journal`

```sql
CREATE TABLE order_journal (
    id INTEGER PRIMARY KEY,
    journal_type VARCHAR(50) NOT NULL,
    order_number INTEGER NOT NULL,
    order_date DATE NOT NULL,
    title TEXT NOT NULL,
    executor VARCHAR(255) NOT NULL,
    program_id INTEGER,
    program_name TEXT,
    notes TEXT,
    created_at DATETIME,
    document_path VARCHAR(500),
    FOREIGN KEY (program_id) REFERENCES programs(id),
    UNIQUE (journal_type, order_number)
);
```

## Troubleshooting

### "Table already exists" during migration
✓ **Normal** — safe to ignore, table already created

### "No module named 'openpyxl'"
```bash
pip install openpyxl
```

### Can't see "Журналы" tab
- Restart application
- Check migration ran successfully
- Check console for errors

### "No errors" but journal not working
1. Check migration output
2. Verify database file exists: `data/database.db`
3. Check table exists:
   ```bash
   sqlite3 data/database.db ".tables"
   ```
   Should see: `order_journal`

## Next Steps

1. Read user guide: `РУКОВОДСТВО_ЖУРНАЛЫ.md`
2. Read implementation details: `JOURNAL_SYSTEM_IMPLEMENTATION.md`
3. Start using the journal system!

## Support

- Check existing documentation
- Review error messages in application
- Verify migration completed successfully
- Check database integrity

## Features Ready to Use

✅ Automatic order numbering
✅ Journal registration
✅ Manual entries
✅ Filtering and search
✅ Excel export
✅ Edit/delete entries
✅ Document linking
✅ Program association

**System ready for production use!**
