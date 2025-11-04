import sqlite3
from pprint import pprint

db_path = 'database/professor_sequoia.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"Connected to {db_path}\n")

# Show all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]
print("Tables found:")
pprint(tables)

print("\n=== Ability Table ===")
cursor.execute("SELECT * FROM ability;")
pprint(cursor.fetchall())

print("\n=== Pokemon Table ===")
cursor.execute("SELECT name, type1, type2, hp, atk, def, spa, spd, spe FROM pokemon;")
pprint(cursor.fetchall())

conn.close()