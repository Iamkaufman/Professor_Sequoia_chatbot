"""
Professor Sequoia - Pokémon VGC Database Setup
Fully populates the professor_sequoia.db file using PokéAPI via the pokebase wrapper.
"""
print("SCRIPT STARTED!")

import os
import sqlite3
import pokebase as pb
import time

DB_PATH = "database/professor_sequoia.db"
DEFAULT_FORMATS = "reg-h,reg-j"

# ============================================================
# DATABASE CREATION
# ============================================================

def create_database():
    """Create and initialize all database tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            effect TEXT,
            allowed_formats TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon (
            pokemon_id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            type1 TEXT NOT NULL,
            type2 TEXT,
            hp INTEGER,
            atk INTEGER,
            def INTEGER,
            spa INTEGER,
            spd INTEGER,
            spe INTEGER,
            ability1 INTEGER,
            ability2 INTEGER,
            ability3 INTEGER,
            weight REAL,
            allowed_formats TEXT,
            FOREIGN KEY (ability1) REFERENCES ability(ability_id),
            FOREIGN KEY (ability2) REFERENCES ability(ability_id),
            FOREIGN KEY (ability3) REFERENCES ability(ability_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moves (
            move_id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            category TEXT,
            power INTEGER,
            acc INTEGER,
            pp INTEGER,
            effect TEXT,
            allowed_formats TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS known_moves (
            pokemon_id INTEGER,
            move_id INTEGER,
            PRIMARY KEY (pokemon_id, move_id),
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(pokemon_id),
            FOREIGN KEY (move_id) REFERENCES moves(move_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS item (
            item_id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            effect TEXT,
            allowed_formats TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS type_matchups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacking_type TEXT NOT NULL,
            defending_type TEXT NOT NULL,
            effectiveness REAL NOT NULL,
            UNIQUE(attacking_type, defending_type)
        )
    ''')

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
            FOREIGN KEY (regulation_id) REFERENCES regulations(regulation_id),
            UNIQUE(pokemon_name, regulation_id, month)
        )
    ''')

    conn.commit()
    print("✓ Database tables created successfully!")
    return conn


# ============================================================
# POPULATION FUNCTIONS
# ============================================================

def populate_abilities(conn):
    cursor = conn.cursor()
    print("Fetching all abilities...")
    
    # Fetch by ID range - most reliable method
    added = 0
    for i in range(1, 400):  # Cover all abilities
        try:
            ability = pb.ability(i)
            
            # Get English description
            desc = "No description available."
            if hasattr(ability, "effect_entries"):
                for entry in ability.effect_entries:
                    if hasattr(entry, "language") and entry.language.name == "en":
                        desc = entry.effect
                        break
            
            cursor.execute(
                "INSERT OR IGNORE INTO ability (ability_id, name, effect, allowed_formats) VALUES (?, ?, ?, ?);",
                (ability.id, ability.name, desc, DEFAULT_FORMATS),
            )
            added += 1
            if added % 25 == 0:
                print(f"  Added {added} abilities...")
                conn.commit()
            
            time.sleep(0.05)
            
        except Exception as e:
            # Skip missing IDs silently
            continue
    
    conn.commit()
    print(f"✓ Successfully populated {added} abilities!\n")


def populate_pokemon(conn):
    """Populate the Pokémon table from PokéAPI."""
    cursor = conn.cursor()
    print("Fetching all Pokémon...")

    count = 0
    # Fetch first 1010 Pokémon (covers all through Gen 9)
    for pokemon_id in range(1, 1011):
        try:
            p = pb.pokemon(pokemon_id)
            types = [t.type.name for t in p.types]
            type1 = types[0] if len(types) > 0 else None
            type2 = types[1] if len(types) > 1 else None

            stats_map = {s.stat.name: s.base_stat for s in p.stats}
            stats = {
                "hp": stats_map.get("hp", 0),
                "atk": stats_map.get("attack", 0),
                "def": stats_map.get("defense", 0),
                "spa": stats_map.get("special-attack", 0),
                "spd": stats_map.get("special-defense", 0),
                "spe": stats_map.get("speed", 0),
            }

            # Get ability IDs
            ability_ids = []
            for ab in p.abilities:
                cursor.execute('SELECT ability_id FROM ability WHERE name = ?', (ab.ability.name,))
                res = cursor.fetchone()
                if res:
                    ability_ids.append(res[0])

            while len(ability_ids) < 3:
                ability_ids.append(None)

            weight = p.weight / 10.0 if p.weight else None

            cursor.execute('''
                INSERT OR REPLACE INTO pokemon
                (pokemon_id, name, type1, type2, hp, atk, def, spa, spd, spe,
                 ability1, ability2, ability3, weight, allowed_formats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p.id, p.name, type1, type2,
                stats["hp"], stats["atk"], stats["def"], stats["spa"],
                stats["spd"], stats["spe"],
                ability_ids[0], ability_ids[1], ability_ids[2],
                weight, DEFAULT_FORMATS
            ))

            count += 1
            if count % 50 == 0:
                print(f"  → Added {count} Pokémon...")
                conn.commit()
            
            time.sleep(0.05)

        except Exception as e:
            # Skip missing IDs
            continue

    conn.commit()
    print(f"✓ Successfully populated {count} Pokémon!\n")


def populate_moves(conn):
    """Populate the moves table."""
    cursor = conn.cursor()
    print("Fetching all moves...")

    count = 0
    # Fetch first 920 moves (covers all current moves)
    for move_id in range(1, 921):
        try:
            move = pb.move(move_id)
            effect = None
            if move.effect_entries:
                effect = move.effect_entries[0].short_effect

            cursor.execute('''
                INSERT OR REPLACE INTO moves
                (move_id, name, type, category, power, acc, pp, effect, allowed_formats)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                move.id, move.name, move.type.name,
                move.damage_class.name if move.damage_class else None,
                move.power, move.accuracy, move.pp, effect, DEFAULT_FORMATS
            ))

            count += 1
            if count % 100 == 0:
                print(f"  → Added {count} moves...")
                conn.commit()
            
            time.sleep(0.05)

        except Exception as e:
            continue

    conn.commit()
    print(f"✓ Successfully populated {count} moves!\n")


def populate_items(conn):
    """Populate item table."""
    cursor = conn.cursor()
    print("Fetching all items...")

    count = 0
    # Fetch first 2000 items
    for item_id in range(1, 2001):
        try:
            item = pb.item(item_id)
            effect = None
            if item.effect_entries:
                effect = item.effect_entries[0].short_effect

            cursor.execute('''
                INSERT OR REPLACE INTO item
                (item_id, name, effect, allowed_formats)
                VALUES (?, ?, ?, ?)
            ''', (item.id, item.name, effect, DEFAULT_FORMATS))

            count += 1
            if count % 100 == 0:
                print(f"  → Added {count} items...")
                conn.commit()
            
            time.sleep(0.05)

        except Exception as e:
            continue

    conn.commit()
    print(f"✓ Successfully populated {count} items!\n")


def populate_known_moves(conn):
    """Link Pokémon to their learnable moves."""
    cursor = conn.cursor()
    print("Linking Pokémon to moves...")

    cursor.execute("SELECT pokemon_id, name FROM pokemon")
    all_pokemon = cursor.fetchall()
    
    count = 0
    for poke_id, poke_name in all_pokemon:
        try:
            p = pb.pokemon(poke_id)
            move_ids = set()
            
            for move_info in p.moves:
                move_name = move_info.move.name
                cursor.execute("SELECT move_id FROM moves WHERE name = ?", (move_name,))
                result = cursor.fetchone()
                if result:
                    move_ids.add(result[0])
            
            for move_id in move_ids:
                cursor.execute(
                    "INSERT OR IGNORE INTO known_moves (pokemon_id, move_id) VALUES (?, ?)",
                    (poke_id, move_id)
                )
            
            count += 1
            if count % 50 == 0:
                print(f"  → Linked {count}/{len(all_pokemon)} Pokémon...")
                conn.commit()
            
            time.sleep(0.05)
            
        except Exception as e:
            continue
    
    conn.commit()
    print(f"✓ Successfully linked {count} Pokémon to their moves!\n")


def populate_type_matchups(conn):
    """Populate type matchup multipliers."""
    cursor = conn.cursor()
    types = ['normal', 'fire', 'water', 'electric', 'grass', 'ice', 'fighting',
             'poison', 'ground', 'flying', 'psychic', 'bug', 'rock', 'ghost',
             'dragon', 'dark', 'steel', 'fairy']

    print("Populating type matchups...")
    for atk_type in types:
        t = pb.type_(atk_type)

        for category, mult in [
            (t.damage_relations.double_damage_to, 2.0),
            (t.damage_relations.half_damage_to, 0.5),
            (t.damage_relations.no_damage_to, 0.0)
        ]:
            for d_type in category:
                cursor.execute('''
                    INSERT OR REPLACE INTO type_matchups
                    (attacking_type, defending_type, effectiveness)
                    VALUES (?, ?, ?)
                ''', (atk_type, d_type.name, mult))

        # Fill in gaps with neutral 1.0
        for def_type in types:
            cursor.execute('''
                INSERT OR IGNORE INTO type_matchups
                (attacking_type, defending_type, effectiveness)
                VALUES (?, ?, ?)
            ''', (atk_type, def_type, 1.0))

    conn.commit()
    print("✓ Type matchups populated successfully!\n")


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    print("Initializing full database build...\n")

    conn = create_database()
    populate_abilities(conn)
    populate_pokemon(conn)
    populate_moves(conn)
    populate_known_moves(conn)
    populate_items(conn)
    populate_type_matchups(conn)

    conn.close()
    print("\n✅ Professor Sequoia database fully populated!")
    print("Database location:", os.path.abspath(DB_PATH))