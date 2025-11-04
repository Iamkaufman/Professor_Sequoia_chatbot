"""
Professor Sequoia - Database Query Functions
Provides helper functions for Discord bot to query the VGC database
"""

import sqlite3
from typing import List, Dict, Optional, Tuple
import json


class PokemonDatabase:
    """Database interface for Professor Sequoia bot"""
    
    def __init__(self, db_path='database/professor_sequoia.db'):
        """Initialize database connection"""
        self.db_path = db_path
    
    def _get_connection(self):
        """Create a new database connection"""
        return sqlite3.connect(self.db_path)
    
    def _dict_factory(self, cursor, row):
        """Convert database rows to dictionaries"""
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}
    
    # ========================================================================
    # POKEMON QUERIES
    # ========================================================================
    
    def get_pokemon(self, pokemon_name: str, format_filter: Optional[str] = None) -> Optional[Dict]:
        """
        Get complete Pokemon data including abilities
        
        Args:
            pokemon_name: Name of the Pokemon
            format_filter: Format to check legality (e.g., "reg-h")
        
        Returns:
            Dictionary with Pokemon data or None if not found
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                p.*,
                a1.name as ability1_name,
                a2.name as ability2_name,
                a3.name as ability3_name
            FROM pokemon p
            LEFT JOIN ability a1 ON p.ability1 = a1.ability_id
            LEFT JOIN ability a2 ON p.ability2 = a2.ability_id
            LEFT JOIN ability a3 ON p.ability3 = a3.ability_id
            WHERE p.name = ?
        '''
        
        cursor.execute(query, (pokemon_name.lower(),))
        result = cursor.fetchone()
        conn.close()
        
        if result and format_filter:
            # Check if Pokemon is legal in the specified format
            if result['allowed_formats'] and format_filter not in result['allowed_formats']:
                return None
        
        return result
    
    def get_pokemon_stats(self, pokemon_name: str) -> Optional[Dict[str, int]]:
        """
        Get just the base stats for a Pokemon
        
        Returns:
            Dictionary with stat names and values
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT hp, atk, def, spa, spd, spe
            FROM pokemon
            WHERE name = ?
        ''', (pokemon_name.lower(),))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'hp': result[0],
                'atk': result[1],
                'def': result[2],
                'spa': result[3],
                'spd': result[4],
                'spe': result[5],
                'bst': sum(result)
            }
        return None
    
    def search_pokemon_by_type(self, type1: str, type2: Optional[str] = None, 
                                format_filter: Optional[str] = None) -> List[Dict]:
        """
        Find Pokemon by type combination
        
        Args:
            type1: Primary type to search for
            type2: Secondary type (optional)
            format_filter: Format to check legality
        
        Returns:
            List of Pokemon matching the type criteria
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        if type2:
            query = '''
                SELECT * FROM pokemon 
                WHERE (type1 = ? AND type2 = ?) OR (type1 = ? AND type2 = ?)
            '''
            params = (type1.lower(), type2.lower(), type2.lower(), type1.lower())
        else:
            query = '''
                SELECT * FROM pokemon 
                WHERE type1 = ? OR type2 = ?
            '''
            params = (type1.lower(), type1.lower())
        
        if format_filter:
            query += ' AND allowed_formats LIKE ?'
            params = params + (f'%{format_filter}%',)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def search_pokemon_by_ability(self, ability_name: str, 
                                   format_filter: Optional[str] = None) -> List[Dict]:
        """
        Find all Pokemon with a specific ability
        
        Args:
            ability_name: Name of the ability
            format_filter: Format to check legality
        
        Returns:
            List of Pokemon with that ability
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        # First get the ability_id
        cursor.execute('SELECT ability_id FROM ability WHERE name = ?', 
                      (ability_name.lower().replace(' ', '-'),))
        ability_result = cursor.fetchone()
        
        if not ability_result:
            conn.close()
            return []
        
        ability_id = ability_result['ability_id']
        
        # Find Pokemon with this ability
        query = '''
            SELECT * FROM pokemon 
            WHERE ability1 = ? OR ability2 = ? OR ability3 = ?
        '''
        params = (ability_id, ability_id, ability_id)
        
        if format_filter:
            query += ' AND allowed_formats LIKE ?'
            params = params + (f'%{format_filter}%',)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    # ========================================================================
    # MOVE QUERIES
    # ========================================================================
    
    def get_move(self, move_name: str, format_filter: Optional[str] = None) -> Optional[Dict]:
        """
        Get move data
        
        Args:
            move_name: Name of the move
            format_filter: Format to check legality
        
        Returns:
            Dictionary with move data or None if not found
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM moves WHERE name = ?', (move_name.lower().replace(' ', '-'),))
        result = cursor.fetchone()
        conn.close()
        
        if result and format_filter:
            if result['allowed_formats'] and format_filter not in result['allowed_formats']:
                return None
        
        return result
    
    def get_pokemon_moves(self, pokemon_name: str, format_filter: Optional[str] = None) -> List[Dict]:
        """
        Get all moves a Pokemon can learn
        
        Args:
            pokemon_name: Name of the Pokemon
            format_filter: Format to check move legality
        
        Returns:
            List of moves the Pokemon can learn
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        query = '''
            SELECT m.*
            FROM moves m
            JOIN known_moves km ON m.move_id = km.move_id
            JOIN pokemon p ON p.pokemon_id = km.pokemon_id
            WHERE p.name = ?
        '''
        params = [pokemon_name.lower()]
        
        if format_filter:
            query += ' AND m.allowed_formats LIKE ?'
            params.append(f'%{format_filter}%')
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def search_moves_by_type(self, move_type: str, category: Optional[str] = None,
                             format_filter: Optional[str] = None) -> List[Dict]:
        """
        Find moves by type and optionally category
        
        Args:
            move_type: Type of move (e.g., "fire", "water")
            category: Move category ("physical", "special", "status")
            format_filter: Format to check legality
        
        Returns:
            List of moves matching criteria
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        query = 'SELECT * FROM moves WHERE type = ?'
        params = [move_type.lower()]
        
        if category:
            query += ' AND category = ?'
            params.append(category.lower())
        
        if format_filter:
            query += ' AND allowed_formats LIKE ?'
            params.append(f'%{format_filter}%')
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_pokemon_stab_moves(self, pokemon_name: str, format_filter: Optional[str] = None) -> List[Dict]:
        """
        Get all STAB moves for a Pokemon
        
        Args:
            pokemon_name: Name of the Pokemon
            format_filter: Format to check legality
        
        Returns:
            List of moves that get STAB bonus
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        # Get Pokemon types
        cursor.execute('SELECT type1, type2 FROM pokemon WHERE name = ?', 
                      (pokemon_name.lower(),))
        pokemon_result = cursor.fetchone()
        
        if not pokemon_result:
            conn.close()
            return []
        
        types = [pokemon_result['type1']]
        if pokemon_result['type2']:
            types.append(pokemon_result['type2'])
        
        # Get moves that match Pokemon's types
        query = '''
            SELECT m.*
            FROM moves m
            JOIN known_moves km ON m.move_id = km.move_id
            JOIN pokemon p ON p.pokemon_id = km.pokemon_id
            WHERE p.name = ? AND m.type IN ({})
        '''.format(','.join('?' * len(types)))
        
        params = [pokemon_name.lower()] + types
        
        if format_filter:
            query += ' AND m.allowed_formats LIKE ?'
            params.append(f'%{format_filter}%')
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    # ========================================================================
    # ABILITY QUERIES
    # ========================================================================
    
    def get_ability(self, ability_name: str) -> Optional[Dict]:
        """
        Get ability data
        
        Args:
            ability_name: Name of the ability
        
        Returns:
            Dictionary with ability data or None if not found
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM ability WHERE name = ?', 
                      (ability_name.lower().replace(' ', '-'),))
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    # ========================================================================
    # ITEM QUERIES
    # ========================================================================
    
    def get_item(self, item_name: str, format_filter: Optional[str] = None) -> Optional[Dict]:
        """
        Get item data
        
        Args:
            item_name: Name of the item
            format_filter: Format to check legality
        
        Returns:
            Dictionary with item data or None if not found
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM item WHERE name = ?', 
                      (item_name.lower().replace(' ', '-'),))
        result = cursor.fetchone()
        conn.close()
        
        if result and format_filter:
            if result['allowed_formats'] and format_filter not in result['allowed_formats']:
                return None
        
        return result
    
    def get_all_items(self, format_filter: Optional[str] = None) -> List[Dict]:
        """
        Get all items
        
        Args:
            format_filter: Format to check legality
        
        Returns:
            List of all items
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        query = 'SELECT * FROM item'
        params = []
        
        if format_filter:
            query += ' WHERE allowed_formats LIKE ?'
            params.append(f'%{format_filter}%')
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    # ========================================================================
    # TYPE MATCHUP QUERIES
    # ========================================================================
    
    def get_type_effectiveness(self, attacking_type: str, defending_type: str) -> float:
        """
        Get type effectiveness multiplier
        
        Args:
            attacking_type: The attacking type
            defending_type: The defending type
        
        Returns:
            Effectiveness multiplier (0.0, 0.5, 1.0, 2.0)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT effectiveness FROM type_matchups 
            WHERE attacking_type = ? AND defending_type = ?
        ''', (attacking_type.lower(), defending_type.lower()))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 1.0
    
    def calculate_defensive_typing(self, type1: str, type2: Optional[str] = None) -> Dict:
        """
        Calculate all defensive matchups for a type combination
        
        Args:
            type1: Primary type
            type2: Secondary type (optional)
        
        Returns:
            Dictionary with weaknesses, resistances, and immunities
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        types_list = ['normal', 'fire', 'water', 'electric', 'grass', 'ice', 
                      'fighting', 'poison', 'ground', 'flying', 'psychic', 
                      'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy']
        
        weaknesses = []
        resistances = []
        immunities = []
        
        for attacking_type in types_list:
            effectiveness = 1.0
            
            # Check against type1
            cursor.execute('''
                SELECT effectiveness FROM type_matchups 
                WHERE attacking_type = ? AND defending_type = ?
            ''', (attacking_type, type1.lower()))
            result = cursor.fetchone()
            if result:
                effectiveness *= result[0]
            
            # Check against type2 if it exists
            if type2:
                cursor.execute('''
                    SELECT effectiveness FROM type_matchups 
                    WHERE attacking_type = ? AND defending_type = ?
                ''', (attacking_type, type2.lower()))
                result = cursor.fetchone()
                if result:
                    effectiveness *= result[0]
            
            # Categorize
            if effectiveness == 0:
                immunities.append(attacking_type)
            elif effectiveness > 1.0:
                weaknesses.append((attacking_type, effectiveness))
            elif effectiveness < 1.0:
                resistances.append((attacking_type, effectiveness))
        
        conn.close()
        
        return {
            'weaknesses': sorted(weaknesses, key=lambda x: x[1], reverse=True),
            'resistances': sorted(resistances, key=lambda x: x[1]),
            'immunities': immunities
        }
    
    def calculate_offensive_coverage(self, move_types: List[str]) -> Dict:
        """
        Calculate offensive type coverage for a set of moves
        
        Args:
            move_types: List of move types
        
        Returns:
            Dictionary showing what types are hit super-effectively, neutrally, etc.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        all_types = ['normal', 'fire', 'water', 'electric', 'grass', 'ice', 
                     'fighting', 'poison', 'ground', 'flying', 'psychic', 
                     'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy']
        
        coverage = {}
        
        for defending_type in all_types:
            best_effectiveness = 0.0
            
            for attacking_type in move_types:
                cursor.execute('''
                    SELECT effectiveness FROM type_matchups 
                    WHERE attacking_type = ? AND defending_type = ?
                ''', (attacking_type.lower(), defending_type))
                
                result = cursor.fetchone()
                if result:
                    effectiveness = result[0]
                    if effectiveness > best_effectiveness:
                        best_effectiveness = effectiveness
            
            coverage[defending_type] = best_effectiveness
        
        conn.close()
        
        # Categorize results
        super_effective = [t for t, eff in coverage.items() if eff >= 2.0]
        neutral = [t for t, eff in coverage.items() if eff == 1.0]
        resisted = [t for t, eff in coverage.items() if 0 < eff < 1.0]
        immune = [t for t, eff in coverage.items() if eff == 0]
        
        return {
            'super_effective': super_effective,
            'neutral': neutral,
            'resisted': resisted,
            'immune': immune,
            'raw_coverage': coverage
        }
    
    # ========================================================================
    # TEAM ANALYSIS QUERIES
    # ========================================================================
    
    def analyze_team_types(self, pokemon_names: List[str]) -> Dict:
        """
        Analyze defensive type coverage of a team
        
        Args:
            pokemon_names: List of Pokemon names on the team
        
        Returns:
            Dictionary with team weaknesses and resistances
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        all_types = ['normal', 'fire', 'water', 'electric', 'grass', 'ice', 
                     'fighting', 'poison', 'ground', 'flying', 'psychic', 
                     'bug', 'rock', 'ghost', 'dragon', 'dark', 'steel', 'fairy']
        
        # Get types for each Pokemon
        team_pokemon = []
        for name in pokemon_names:
            cursor.execute('SELECT type1, type2 FROM pokemon WHERE name = ?', 
                          (name.lower(),))
            result = cursor.fetchone()
            if result:
                team_pokemon.append({
                    'name': name,
                    'type1': result[0],
                    'type2': result[1]
                })
        
        # Count how many Pokemon are weak/resistant to each type
        type_analysis = {}
        
        for attacking_type in all_types:
            weak_count = 0
            resist_count = 0
            immune_count = 0
            
            for pkmn in team_pokemon:
                effectiveness = 1.0
                
                # Check type1
                cursor.execute('''
                    SELECT effectiveness FROM type_matchups 
                    WHERE attacking_type = ? AND defending_type = ?
                ''', (attacking_type, pkmn['type1']))
                result = cursor.fetchone()
                if result:
                    effectiveness *= result[0]
                
                # Check type2 if exists
                if pkmn['type2']:
                    cursor.execute('''
                        SELECT effectiveness FROM type_matchups 
                        WHERE attacking_type = ? AND defending_type = ?
                    ''', (attacking_type, pkmn['type2']))
                    result = cursor.fetchone()
                    if result:
                        effectiveness *= result[0]
                
                if effectiveness == 0:
                    immune_count += 1
                elif effectiveness > 1.0:
                    weak_count += 1
                elif effectiveness < 1.0:
                    resist_count += 1
            
            type_analysis[attacking_type] = {
                'weak': weak_count,
                'resist': resist_count,
                'immune': immune_count
            }
        
        conn.close()
        
        # Identify major weaknesses (3+ Pokemon weak)
        major_weaknesses = [t for t, data in type_analysis.items() if data['weak'] >= 3]
        
        # Identify good resistances (3+ Pokemon resist)
        good_resistances = [t for t, data in type_analysis.items() if data['resist'] >= 3]
        
        return {
            'detailed_analysis': type_analysis,
            'major_weaknesses': major_weaknesses,
            'good_resistances': good_resistances,
            'team_size': len(team_pokemon)
        }
    
    def get_speed_tier(self, speed_value: int, format_filter: Optional[str] = None) -> List[Dict]:
        """
        Get Pokemon faster or slower than a given speed value
        
        Args:
            speed_value: Speed stat to compare
            format_filter: Format to check legality
        
        Returns:
            List of Pokemon with their speed stats
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()
        
        query = 'SELECT name, spe FROM pokemon WHERE spe >= ? ORDER BY spe DESC'
        params = [speed_value]
        
        if format_filter:
            query = query.replace('ORDER BY', 'AND allowed_formats LIKE ? ORDER BY')
            params.append(f'%{format_filter}%')
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return results