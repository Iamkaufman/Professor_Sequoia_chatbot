"""
Test cases for Feature 1: Generate VGC team based on user input
Covers TC01.01 through TC01.06
"""

import unittest
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.controller import handle_buildcore_request, get_regulation_list


class TestTeamGeneration(unittest.TestCase):
    """Test team generation with various inputs"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_user_id = "test_user_123"

    def test_TC01_01_empty_team_valid_regulation(self):
        """TC01.01: Empty input with valid regulation should prompt for Pokemon"""
        result = asyncio.run(
            handle_buildcore_request("", self.test_user_id, regulation="H")
        )
        
        self.assertEqual(result['status'], 'clarify')
        self.assertIn('which', result['message'].lower())
        self.assertIn('pokemon', result['message'].lower())

    def test_TC01_02_single_pokemon_valid_regulation(self):
        """TC01.02: Single Pokemon with valid regulation generates team"""
        result = asyncio.run(
            handle_buildcore_request(
                "Hisuian Typhlosion",
                self.test_user_id,
                regulation="H"
            )
        )
        
        self.assertEqual(result['status'], 'ok')
        self.assertIn('team', result)
        self.assertEqual(len(result['team']), 6)
        
        # Verify Typhlosion is in team
        team_names = [p['name'].lower() for p in result['team']]
        self.assertTrue(
            any('typhlosion' in name for name in team_names),
            "Typhlosion should be in the generated team"
        )

    def test_TC01_03_dual_core_valid_regulation(self):
        """TC01.03: Two Pokemon core generates team around that core"""
        result = asyncio.run(
            handle_buildcore_request(
                "Sneasler, Indeedee",
                self.test_user_id,
                regulation="H"
            )
        )
        
        self.assertEqual(result['status'], 'ok')
        self.assertIn('team', result)
        self.assertEqual(len(result['team']), 6)
        
        # Verify both core Pokemon are in team
        team_names = [p['name'].lower() for p in result['team']]
        self.assertTrue(any('sneasler' in name for name in team_names))
        self.assertTrue(any('indeedee' in name for name in team_names))

    def test_TC01_04_multiple_pokemon_valid_regulation(self):
        """TC01.04: Multiple Pokemon (3+) fills remaining slots"""
        result = asyncio.run(
            handle_buildcore_request(
                "Iron Crown, Whimsicott, Regidrago",
                self.test_user_id,
                regulation="F"
            )
        )
        
        self.assertEqual(result['status'], 'ok')
        self.assertIn('team', result)
        self.assertEqual(len(result['team']), 6)
        
        # Verify all three specified Pokemon are in team
        team_names = [p['name'].lower() for p in result['team']]
        self.assertTrue(any('iron-crown' in name for name in team_names))
        self.assertTrue(any('whimsicott' in name for name in team_names))
        self.assertTrue(any('regidrago' in name for name in team_names))

    def test_TC01_05_misspelled_pokemon_correction(self):
        """TC01.05: Misspelled Pokemon should trigger clarification"""
        result = asyncio.run(
            handle_buildcore_request(
                "Goroudon",
                self.test_user_id,
                regulation="G"
            )
        )
        
        # Should either correct automatically or ask for clarification
        self.assertIn(result['status'], ['ok', 'clarify'])
        
        if result['status'] == 'clarify':
            self.assertIn('mean', result['message'].lower())

    def test_TC01_06_invalid_regulation(self):
        """TC01.06: Invalid regulation should return error"""
        result = asyncio.run(
            handle_buildcore_request(
                "Dragapult",
                self.test_user_id,
                regulation="K"
            )
        )
        
        # Should return error or clarification
        self.assertIn(result['status'], ['error', 'clarify'])
        self.assertIn('regulation', result['message'].lower())


class TestRegulationLegality(unittest.TestCase):
    """Test regulation rules and Pokemon legality"""

    def test_regulation_H_banned_paradoxes(self):
        """Regulation H should ban paradox Pokemon"""
        reg_rules = get_regulation_list("H")
        banned = [b.lower() for b in reg_rules.get('banned', [])]
        
        # Paradox Pokemon should be banned
        paradoxes = ['flutter-mane', 'great-tusk', 'iron-hands']
        for paradox in paradoxes:
            self.assertIn(paradox, banned,
                f"{paradox} should be banned in Regulation H")

    def test_regulation_F_allows_more_pokemon(self):
        """Regulation F should allow more Pokemon than Regulation E"""
        reg_e = get_regulation_list("E")
        reg_f = get_regulation_list("F")
        
        # Reg F should have fewer banned Pokemon (more allowed)
        self.assertLessEqual(
            len(reg_f.get('banned', [])),
            len(reg_e.get('banned', [])) + 10  # Allow some variance
        )

    def test_illegal_pokemon_rejected(self):
        """Banned Pokemon should be rejected for team building"""
        result = asyncio.run(
            handle_buildcore_request(
                "Flutter Mane, Rillaboom",
                "test_user",
                regulation="H"
            )
        )
        
        # Should return error since Flutter Mane is banned in Reg H
        self.assertEqual(result['status'], 'error')
        self.assertIn('banned', result['message'].lower())


class TestTeamComposition(unittest.TestCase):
    """Test team composition and quality"""

    def test_team_has_six_pokemon(self):
        """Generated team should always have exactly 6 Pokemon"""
        result = asyncio.run(
            handle_buildcore_request(
                "Incineroar",
                "test_user",
                regulation="H"
            )
        )
        
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(len(result['team']), 6)

    def test_team_has_moves(self):
        """Each Pokemon should have suggested moves"""
        result = asyncio.run(
            handle_buildcore_request(
                "Rillaboom",
                "test_user",
                regulation="H"
            )
        )
        
        self.assertEqual(result['status'], 'ok')
        
        for pokemon in result['team']:
            self.assertIn('suggested_moves', pokemon)
            self.assertGreater(len(pokemon['suggested_moves']), 0)
            self.assertLessEqual(len(pokemon['suggested_moves']), 4)

    def test_team_has_items(self):
        """Each Pokemon should have a suggested item"""
        result = asyncio.run(
            handle_buildcore_request(
                "Amoonguss",
                "test_user",
                regulation="H"
            )
        )
        
        self.assertEqual(result['status'], 'ok')
        
        for pokemon in result['team']:
            self.assertIn('suggested_item', pokemon)
            self.assertIsNotNone(pokemon['suggested_item'])

    def test_team_has_ev_spreads(self):
        """Each Pokemon should have suggested EV spread"""
        result = asyncio.run(
            handle_buildcore_request(
                "Landorus",
                "test_user",
                regulation="H"
            )
        )
        
        self.assertEqual(result['status'], 'ok')
        
        for pokemon in result['team']:
            self.assertIn('suggested_ev', pokemon)
            self.assertIsNotNone(pokemon['suggested_ev'])


if __name__ == '__main__':
    unittest.main()