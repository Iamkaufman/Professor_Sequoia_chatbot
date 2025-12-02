"""
Test cases for Use Case 3: Provide Strategic Advice
Tests the StrategyEngine for tactical recommendations
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cogs.strategy import StrategyEngine


class TestGenericStrategy(unittest.TestCase):
    """Test generic strategy advice without team"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = StrategyEngine(repo=None)

    def test_generic_strategy_no_target(self):
        """Test generic strategy without specific target"""
        result = self.engine.generic_strategy(target=None)
        
        self.assertEqual(result['mode'], 'generic')
        self.assertIn('advice', result)
        self.assertGreater(len(result['advice']), 0)
        
        # Should include universal principles
        advice_text = ' '.join(result['advice'])
        self.assertIn('win condition', advice_text.lower())

    def test_generic_strategy_dondozo_tatsugiri(self):
        """Test strategy against Dondozo-Tatsugiri archetype"""
        result = self.engine.generic_strategy(target="Dondozo-Tatsugiri")
        
        self.assertEqual(result['mode'], 'generic-archetype')
        self.assertEqual(result['archetype'], 'Dondozo-Tatsugiri')
        self.assertIn('advice', result)
        
        # Should mention specific counters
        advice_text = ' '.join(result['advice'])
        self.assertIn('Unaware', advice_text)

    def test_generic_strategy_unknown_target(self):
        """Test strategy against unrecognized target"""
        result = self.engine.generic_strategy(target="RandomPokemon")
        
        self.assertEqual(result['mode'], 'generic')
        self.assertIn('advice', result)
        self.assertIn('RandomPokemon', result['advice'][0])


class TestTeamBasedStrategy(unittest.TestCase):
    """Test strategy analysis with team data"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = StrategyEngine(repo=None)
        
        self.sample_team = [
            {
                'name': 'Incineroar',
                'spe': 60,
                'atk': 115,
                'spa': 60,
                'hp': 95,
                'def': 90,
                'spd': 90,
                'moves': ['Fake Out', 'Flare Blitz', 'Knock Off', 'Parting Shot']
            },
            {
                'name': 'Rillaboom',
                'spe': 85,
                'atk': 125,
                'spa': 60,
                'hp': 100,
                'def': 90,
                'spd': 70,
                'moves': ['Grassy Glide', 'Fake Out', 'Wood Hammer', 'U-turn']
            },
            {
                'name': 'Amoonguss',
                'spe': 30,
                'atk': 85,
                'spa': 85,
                'hp': 114,
                'def': 70,
                'spd': 80,
                'moves': ['Spore', 'Rage Powder', 'Pollen Puff', 'Protect']
            },
            {
                'name': 'Tornadus',
                'spe': 121,
                'atk': 115,
                'spa': 125,
                'hp': 79,
                'def': 70,
                'spd': 80,
                'moves': ['Tailwind', 'Bleakwind Storm', 'Taunt', 'Protect']
            },
            {
                'name': 'Landorus-Therian',
                'spe': 91,
                'atk': 145,
                'spa': 105,
                'hp': 89,
                'def': 90,
                'spd': 80,
                'moves': ['Earthquake', 'Rock Slide', 'U-turn', 'Protect']
            },
            {
                'name': 'Gholdengo',
                'spe': 84,
                'atk': 60,
                'spa': 133,
                'hp': 87,
                'def': 95,
                'spd': 91,
                'moves': ['Make It Rain', 'Shadow Ball', 'Protect', 'Nasty Plot']
            }
        ]

    def test_analyze_strategy_full_team(self):
        """Test strategy analysis with full team"""
        result = self.engine.analyze_strategy(self.sample_team)
        
        self.assertEqual(result['mode'], 'team')
        self.assertIn('roles', result)
        self.assertIn('recommended_leads', result)
        self.assertIn('tera_notes', result)
        self.assertIn('win_conditions', result)
        
        # Should identify 6 roles
        self.assertEqual(len(result['roles']), 6)

    def test_identify_roles(self):
        """Test role identification"""
        roles = self.engine.identify_roles(self.sample_team)
        
        self.assertEqual(len(roles), 6)
        
        # Check specific role identifications
        role_dict = {name: role for name, role in roles}
        
        # Tornadus should be fast attacker
        self.assertIn('Fast Attacker', role_dict['Tornadus'])
        
        # Amoonguss should be bulky or support
        self.assertIn('Bulky', role_dict.get('Amoonguss', ''))

    def test_recommend_leads(self):
        """Test lead recommendation"""
        roles = self.engine.identify_roles(self.sample_team)
        leads = self.engine.recommend_leads(self.sample_team, roles)
        
        self.assertGreater(len(leads), 0)
        
        # Should recommend Fake Out + redirection
        first_lead = leads[0]
        self.assertIn('pair', first_lead)
        
        # Should include Incineroar or Rillaboom (Fake Out)
        # and Amoonguss (Rage Powder)
        if first_lead['pair']:
            self.assertTrue(
                'Incineroar' in first_lead['pair'] or 'Rillaboom' in first_lead['pair']
            )

    def test_identify_win_conditions(self):
        """Test win condition identification"""
        wincons = self.engine.identify_win_conditions(self.sample_team)
        
        self.assertGreater(len(wincons), 0)
        
        # Should identify Landorus-T (145 Atk) as physical wincon
        land_wincon = any('Landorus' in wc for wc in wincons)
        self.assertTrue(land_wincon)
        
        # Should identify Gholdengo (133 SpA) as special wincon
        ghol_wincon = any('Gholdengo' in wc for wc in wincons)
        self.assertTrue(ghol_wincon)

    def test_matchup_specific_calyrex(self):
        """Test matchup-specific advice vs Calyrex-Shadow"""
        result = self.engine.analyze_strategy(
            self.sample_team,
            target="Calyrex-Shadow"
        )
        
        self.assertIsNotNone(result['matchup_specific'])
        
        matchup_notes = result['matchup_specific']
        # Should mention Dark-types and Trick Room
        notes_text = ' '.join(matchup_notes)
        self.assertIn('Dark', notes_text)

    def test_matchup_specific_dondozo(self):
        """Test matchup-specific advice vs Dondozo-Tatsugiri"""
        notes = self.engine.matchup_specific(
            self.sample_team,
            target="Dondozo-Tatsugiri"
        )
        
        self.assertGreater(len(notes), 0)
        
        notes_text = ' '.join(notes)
        # Should mention Unaware or setup avoidance
        self.assertTrue('Unaware' in notes_text or 'setup' in notes_text.lower())

    def test_matchup_specific_iron_hands(self):
        """Test matchup-specific advice vs Iron Hands"""
        notes = self.engine.matchup_specific(
            self.sample_team,
            target="Iron Hands"
        )
        
        self.assertGreater(len(notes), 0)
        
        notes_text = ' '.join(notes)
        # Should mention Ground or Fairy coverage
        self.assertTrue('Ground' in notes_text or 'Fairy' in notes_text)


class TestRoleIdentification(unittest.TestCase):
    """Test specific role identification logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = StrategyEngine(repo=None)

    def test_identify_trick_room_pokemon(self):
        """Test identification of Trick Room Pokemon"""
        team = [
            {
                'name': 'Cresselia',
                'spe': 85,
                'atk': 70,
                'spa': 75,
                'hp': 120,
                'def': 120,
                'spd': 130,
                'moves': ['Trick Room', 'Moonblast', 'Psychic', 'Helping Hand']
            }
        ]
        
        roles = self.engine.identify_roles(team)
        
        self.assertEqual(len(roles), 1)
        # Should identify as Trick Room setter
        self.assertIn('Trick Room', roles[0][1])

    def test_identify_slow_pokemon(self):
        """Test identification of naturally slow Pokemon"""
        team = [
            {
                'name': 'Torkoal',
                'spe': 20,
                'atk': 85,
                'spa': 85,
                'hp': 70,
                'def': 140,
                'spd': 70,
                'moves': ['Eruption', 'Heat Wave', 'Earth Power', 'Protect']
            }
        ]
        
        roles = self.engine.identify_roles(team)
        
        # Should identify as Trick Room compatible
        self.assertIn('Trick Room', roles[0][1])

    def test_identify_fast_attacker(self):
        """Test identification of fast attackers"""
        team = [
            {
                'name': 'Dragapult',
                'spe': 142,
                'atk': 120,
                'spa': 100,
                'hp': 88,
                'def': 75,
                'spd': 75,
                'moves': ['Dragon Darts', 'Phantom Force', 'U-turn', 'Protect']
            }
        ]
        
        roles = self.engine.identify_roles(team)
        
        # Should identify as fast attacker
        self.assertIn('Fast Attacker', roles[0][1])

    def test_identify_bulky_pivot(self):
        """Test identification of bulky pivots"""
        team = [
            {
                'name': 'Gastrodon',
                'spe': 39,
                'atk': 83,
                'spa': 92,
                'hp': 111,
                'def': 68,
                'spd': 82,
                'moves': ['Earth Power', 'Ice Beam', 'Recover', 'Protect']
            }
        ]
        
        roles = self.engine.identify_roles(team)
        
        # Should identify as bulky (high combined bulk)
        self.assertIn('Bulky', roles[0][1])


class TestTeraRecommendations(unittest.TestCase):
    """Test Tera type recommendations"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = StrategyEngine(repo=None)

    def test_recommend_tera_with_data(self):
        """Test Tera recommendations when Tera types are specified"""
        team = [
            {
                'name': 'Gholdengo',
                'spe': 84,
                'atk': 60,
                'spa': 133,
                'hp': 87,
                'def': 95,
                'spd': 91,
                'moves': [],
                'module': {'tera_type': 'Steel'}
            },
            {
                'name': 'Landorus-Therian',
                'spe': 91,
                'atk': 145,
                'spa': 105,
                'hp': 89,
                'def': 90,
                'spd': 80,
                'moves': [],
                'tera_type': 'Flying'
            }
        ]
        
        roles = self.engine.identify_roles(team)
        tera_notes = self.engine.recommend_tera(team, roles)
        
        self.assertGreater(len(tera_notes), 0)
        
        # Should mention both Tera types
        notes_text = ' '.join(tera_notes)
        self.assertIn('Steel', notes_text)
        self.assertIn('Flying', notes_text)

    def test_recommend_tera_without_data(self):
        """Test Tera recommendations when no Tera types specified"""
        team = [
            {
                'name': 'Incineroar',
                'spe': 60,
                'atk': 115,
                'spa': 60,
                'hp': 95,
                'def': 90,
                'spd': 90,
                'moves': []
            }
        ]
        
        roles = self.engine.identify_roles(team)
        tera_notes = self.engine.recommend_tera(team, roles)
        
        # Should return empty or minimal notes
        self.assertIsInstance(tera_notes, list)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = StrategyEngine(repo=None)

    def test_empty_team(self):
        """Test analysis with empty team"""
        result = self.engine.analyze_strategy([])
        
        self.assertEqual(result['mode'], 'team')
        self.assertEqual(len(result['roles']), 0)
        self.assertIsInstance(result['recommended_leads'], list)

    def test_incomplete_pokemon_data(self):
        """Test analysis with incomplete Pokemon data"""
        team = [
            {
                'name': 'Pikachu',
                # Missing stats
                'moves': []
            }
        ]
        
        # Should not crash
        roles = self.engine.identify_roles(team)
        self.assertEqual(len(roles), 1)

    def test_no_moves_specified(self):
        """Test analysis when Pokemon have no moves"""
        team = [
            {
                'name': 'Charizard',
                'spe': 100,
                'atk': 84,
                'spa': 109,
                'hp': 78,
                'def': 78,
                'spd': 85,
                'moves': []
            }
        ]
        
        roles = self.engine.identify_roles(team)
        leads = self.engine.recommend_leads(team, roles)
        
        # Should still provide some analysis
        self.assertEqual(len(roles), 1)
        self.assertGreater(len(leads), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)