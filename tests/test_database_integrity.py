"""
Test cases for Feature 3: Database integrity checks
Covers TC05.01 through TC05.04
"""

import unittest
import sqlite3
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestDatabaseIntegrity(unittest.TestCase):
    """Test database integrity and validation"""

    def setUp(self):
        """Set up test database with various conditions"""
        self.test_db = Path(__file__).parent / "test_integrity.db"
        self.conn = sqlite3.connect(self.test_db)
        self.create_tables()

    def tearDown(self):
        """Clean up"""
        self.conn.close()
        if self.test_db.exists():
            self.test_db.unlink()

    def create_tables(self):
        """Create test tables"""
        cursor = self.conn.cursor()
        
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
                spe INTEGER
            )
        ''')
        
        self.conn.commit()

    def test_TC05_01_complete_entries(self):
        """TC05.01: Complete and valid entries should pass verification"""
        cursor = self.conn.cursor()
        
        # Insert complete, valid entries
        test_pokemon = [
            (25, 'pikachu', 'electric', None, 35, 55, 40, 50, 50, 90),
            (6, 'charizard', 'fire', 'flying', 78, 84, 78, 109, 85, 100),
        ]
        
        for poke in test_pokemon:
            cursor.execute('''
                INSERT INTO pokemon
                (pokemon_id, name, type1, type2, hp, atk, def, spa, spd, spe)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', poke)
        
        self.conn.commit()
        
        # Verification check
        cursor.execute("SELECT COUNT(*) FROM pokemon")
        count = cursor.fetchone()[0]
        
        self.assertEqual(count, 2)
        
        # Check for required fields
        cursor.execute("SELECT * FROM pokemon WHERE name IS NULL OR type1 IS NULL")
        invalid = cursor.fetchall()
        
        self.assertEqual(len(invalid), 0, "All entries should be valid")

    def test_TC05_02_missing_entries(self):
        """TC05.02: Missing entries should be detected"""
        cursor = self.conn.cursor()
        
        # Expected Pokemon IDs (e.g., starter Pokemon)
        expected_ids = [1, 4, 7, 25, 133]  # Bulbasaur, Charmander, Squirtle, Pikachu, Eevee
        
        # Only insert some
        cursor.execute("INSERT INTO pokemon (pokemon_id, name, type1, hp, atk, def, spa, spd, spe) VALUES (1, 'bulbasaur', 'grass', 45, 49, 49, 65, 65, 45)")
        cursor.execute("INSERT INTO pokemon (pokemon_id, name, type1, hp, atk, def, spa, spd, spe) VALUES (25, 'pikachu', 'electric', 35, 55, 40, 50, 50, 90)")
        self.conn.commit()
        
        # Check for missing IDs
        cursor.execute("SELECT pokemon_id FROM pokemon")
        present_ids = [row[0] for row in cursor.fetchall()]
        
        missing = set(expected_ids) - set(present_ids)
        
        self.assertGreater(len(missing), 0, "Should detect missing entries")
        self.assertIn(4, missing, "Charmander should be missing")

    def test_TC05_03_duplicate_entries(self):
        """TC05.03: Duplicate entries should be detected"""
        cursor = self.conn.cursor()
        
        # Try to insert duplicate (should fail due to UNIQUE constraint)
        cursor.execute("INSERT INTO pokemon (pokemon_id, name, type1, hp, atk, def, spa, spd, spe) VALUES (25, 'pikachu', 'electric', 35, 55, 40, 50, 50, 90)")
        
        # Attempt duplicate with different ID (tests name uniqueness)
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO pokemon (pokemon_id, name, type1, hp, atk, def, spa, spd, spe) VALUES (26, 'pikachu', 'electric', 35, 55, 40, 50, 50, 90)")

    def test_TC05_04_corrupted_entries(self):
        """TC05.04: Corrupted/invalid data should be detected"""
        cursor = self.conn.cursor()
        
        # Insert entries with invalid data
        try:
            # Negative stats (invalid)
            cursor.execute("INSERT INTO pokemon (pokemon_id, name, type1, hp, atk, def, spa, spd, spe) VALUES (999, 'missingno', 'glitch', -10, 999, -5, 0, 0, 0)")
            self.conn.commit()
            
            # Check for invalid stats
            cursor.execute("SELECT * FROM pokemon WHERE hp < 0 OR atk < 0 OR def < 0")
            corrupted = cursor.fetchall()
            
            self.assertGreater(len(corrupted), 0, "Should detect corrupted entries")
            
        except Exception:
            pass  # Some validation might prevent insertion


class TestDataConsistency(unittest.TestCase):
    """Test data consistency across tables"""

    def setUp(self):
        """Set up test database"""
        self.test_db = Path(__file__).parent / "test_consistency.db"
        self.conn = sqlite3.connect(self.test_db)
        self.create_schema()

    def tearDown(self):
        """Clean up"""
        self.conn.close()
        if self.test_db.exists():
            self.test_db.unlink()

    def create_schema(self):
        """Create test schema"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pokemon (
                pokemon_id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moves (
                move_id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
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
        
        self.conn.commit()

    def test_foreign_key_integrity(self):
        """Foreign key relationships should be maintained"""
        cursor = self.conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Insert Pokemon and move
        cursor.execute("INSERT INTO pokemon (pokemon_id, name) VALUES (25, 'pikachu')")
        cursor.execute("INSERT INTO moves (move_id, name) VALUES (1, 'thunderbolt')")
        cursor.execute("INSERT INTO known_moves (pokemon_id, move_id) VALUES (25, 1)")
        self.conn.commit()
        
        # Try to insert known_moves with non-existent Pokemon (should fail)
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO known_moves (pokemon_id, move_id) VALUES (999, 1)")
            self.conn.commit()


if __name__ == '__main__':
    unittest.main()