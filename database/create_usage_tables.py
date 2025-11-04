import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "professor_sequoia.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Adding missing tables...")

cursor.execute('''
    CREATE TABLE IF NOT EXISTS regulations (
        regulation_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        allowed_pokemon TEXT,
        restricted_pokemon TEXT,
        banned_pokemon TEXT,
        start_date TEXT,
        end_date TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS usage_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pokemon_name TEXT NOT NULL,
        regulation_id TEXT NOT NULL,
        usage_percent REAL,
        rank INTEGER,
        month TEXT,
        UNIQUE(pokemon_name, regulation_id, month)
    )
''')

conn.commit()
conn.close()

print("✅ Tables added successfully!")