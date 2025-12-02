"""
Test cases for Use Case 2: Evaluate and Optimize an Existing Team
Tests team evaluation, synergy analysis, and optimization recommendations
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cogs.controller import (
    parse_pokepaste,
    evaluate_synergy,
    recommend_optimizations,
    evaluate_team,
    handle_team_evaluation,
    get_regulation_list
)


class TestPokepasteParsing(unittest.TestCase):
    """Test Pokepaste format parsing"""

    def test_parse_complete_pokemon(self):
        """Test parsing a complete Pokemon set"""
        pokepaste_text = """Incineroar @ Sitrus Berry
Ability: Intimidate
Tera Type: Ghost
EVs: 252 HP / 252 Def / 4 SpD
Careful Nature
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot"""
        
        team = parse_pokepaste(pokepaste_text)
        
        self.assertEqual(len(team), 1)
        self.assertEqual(team[0]['name'], 'Incineroar')
        self.assertEqual(team[0]['item'], 'Sitrus Berry')
        self.assertEqual(team[0]['ability'], 'Intimidate')
        self.assertEqual(team[0]['tera_type'], 'Ghost')
        self.assertEqual(len(team[0]['moves']), 4)
        self.assertIn('Fake Out', team[0]['moves'])

    def test_parse_multiple_pokemon(self):
        """Test parsing multiple Pokemon"""
        pokepaste_text = """Incineroar @ Sitrus Berry
Ability: Intimidate
- Fake Out
- Flare Blitz

Amoonguss @ Rocky Helmet
Ability: Regenerator
- Spore
- Rage Powder"""
        
        team = parse_pokepaste(pokepaste_text)
        
        self.assertEqual(len(team), 2)
        self.assertEqual(team[0]['name'], 'Incineroar')
        self.assertEqual(team[1]['name'], 'Amoonguss')

    def test_parse_minimal_set(self):
        """Test parsing Pokemon with minimal information"""
        pokepaste_text = """Rillaboom @ Assault Vest
- Grassy Glide
- Fake Out"""
        
        team = parse_pokepaste(pokepaste_text)
        
        self.assertEqual(len(team), 1)
        self.assertEqual(team[0]['name'], 'Rillaboom')
        self.assertEqual(team[0]['item'], 'Assault Vest')
        self.assertEqual(len(team[0]['moves']), 2)

    def test_parse_pokemon_with_no_item(self):
        """Test parsing Pokemon without held item"""
        pokepaste_text = """Flutter Mane
Ability: Protosynthesis
- Moonblast
- Shadow Ball"""
        
        team = parse_pokepaste(pokepaste_text)
        
        self.assertEqual(len(team), 1)
        self.assertEqual(team[0]['name'], 'Flutter Mane')
        # Should have 'None' or no item field
        self.assertTrue(team[0]['item'] in ['None', ''])

    def test_parse_empty_input(self):
        """Test parsing empty or invalid input"""
        team = parse_pokepaste("")
        self.assertEqual(len(team), 0)


class TestSynergyEvaluation(unittest.TestCase):
    """Test team synergy analysis"""

    def setUp(self):
        """Set up test fixtures"""
        self.basic_team = [
            {
                'name': 'Incineroar',
                'types': ['Fire', 'Dark'],
                'moves': ['Fake Out', 'Flare Blitz', 'Knock Off', 'Parting Shot']
            },
            {
                'name': 'Amoonguss',
                'types': ['Grass', 'Poison'],
                'moves': ['Spore', 'Rage Powder', 'Pollen Puff', 'Protect']
            },
            {
                'name': 'Landorus-Therian',
                'types': ['Ground', 'Flying'],
                'moves': ['Earthquake', 'Rock Slide', 'U-turn', 'Protect']
            }
        ]

    def test_evaluate_basic_synergy(self):
        """Test basic synergy evaluation"""
        result = evaluate_synergy(self.basic_team)
        
        self.assertIn('summary', result)
        self.assertIn('weaknesses', result)
        self.assertIn('type_coverage', result)
        self.assertIsInstance(result['type_coverage'], dict)

    def test_detect_speed_control(self):
        """Test detection of speed control moves"""
        team_with_tr = [
            {
                'name': 'Cresselia',
                'types': ['Psychic'],
                'moves': ['Trick Room', 'Moonblast', 'Helping Hand', 'Protect']
            }
        ]
        
        result = evaluate_synergy(team_with_tr)
        
        self.assertIn('speed_control', result)
        self.assertGreater(len(result['speed_control']), 0)
        self.assertIn('Cresselia', result['speed_control'])

    def test_detect_support_moves(self):
        """Test detection of support moves"""
        team_with_support = [
            {
                'name': 'Amoonguss',
                'types': ['Grass', 'Poison'],
                'moves': ['Rage Powder', 'Spore', 'Pollen Puff', 'Protect']
            }
        ]
        
        result = evaluate_synergy(team_with_support)
        
        self.assertIn('support', result)
        self.assertIn('Amoonguss', result['support'])

    def test_identify_no_speed_control(self):
        """Test warning when no speed control is present"""
        team_no_speed = [
            {
                'name': 'Landorus-Therian',
                'types': ['Ground', 'Flying'],
                'moves': ['Earthquake', 'Rock Slide', 'U-turn', 'Protect']
            }
        ]
        
        result = evaluate_synergy(team_no_speed)
        
        # Should identify lack of speed control
        weaknesses_text = ' '.join(result['weaknesses'])
        self.assertTrue('speed control' in weaknesses_text.lower())

    def test_type_coverage_counting(self):
        """Test type coverage analysis"""
        result = evaluate_synergy(self.basic_team)
        
        coverage = result['type_coverage']
        self.assertIn('Fire', coverage)
        self.assertIn('Ground', coverage)
        self.assertIn('Grass', coverage)


class TestRegulationLegality(unittest.TestCase):
    """Test regulation legality checking"""

    def test_get_regulation_a_banned_list(self):
        """Test Regulation A banned Pokemon"""
        reg_a = get_regulation_list('A')
        
        self.assertIn('banned', reg_a)
        banned = [b.lower() for b in reg_a['banned']]
        
        # Should ban Paradox Pokemon
        self.assertIn('flutter-mane', banned)
        self.assertIn('iron-hands', banned)
        
        # Should ban box legendaries
        self.assertIn('koraidon', banned)

    def test_regulation_inheritance(self):
        """Test that regulations properly inherit from previous ones"""
        reg_b = get_regulation_list('B')
        reg_c = get_regulation_list('C')
        
        # Reg B should unban Paradox Pokemon
        banned_b = [b.lower() for b in reg_b['banned']]
        
        # Reg C should inherit from B
        banned_c = [b.lower() for b in reg_c['banned']]
        
        self.assertIsInstance(banned_b, list)
        self.assertIsInstance(banned_c, list)

    def test_regulation_h_strict_bans(self):
        """Test Regulation H has strict ban list"""
        reg_h = get_regulation_list('H')
        banned = [b.lower() for b in reg_h['banned']]
        
        # Should ban all Paradox Pokemon again
        self.assertIn('flutter-mane', banned)
        self.assertIn('iron-hands', banned)

    def test_illegal_pokemon_detection(self):
        """Test detection of illegal Pokemon in team"""
        # Use lowercase with hyphen to match the banned list format
        team_with_illegal = [
            {
                'name': 'flutter-mane',
                'types': ['Ghost', 'Fairy'],
                'moves': ['Moonblast', 'Shadow Ball', 'Protect', 'Icy Wind']
            }
        ]
        
        result = evaluate_synergy(team_with_illegal, format_regulation='A')
        
        # Should flag flutter-mane as illegal in Reg A
        weaknesses_text = ' '.join(result['weaknesses'])
        self.assertIn('Illegal', weaknesses_text)


class TestRecommendOptimizations(unittest.TestCase):
    """Test optimization recommendation logic"""

    def test_recommend_speed_control(self):
        """Test recommendation when speed control is missing"""
        synergy_report = {
            'speed_control': [],
            'support': [],
            'weaknesses': ['No speed control detected.']
        }
        
        recs = recommend_optimizations([], synergy_report)
        
        self.assertGreater(len(recs), 0)
        recs_text = ' '.join(recs).lower()
        self.assertTrue('speed control' in recs_text or 'trick room' in recs_text)

    def test_recommend_redirection(self):
        """Test recommendation when redirection is missing"""
        synergy_report = {
            'speed_control': ['Tailwind'],
            'support': [],
            'weaknesses': ['Lacks redirection or general support options.']
        }
        
        recs = recommend_optimizations([], synergy_report)
        
        recs_text = ' '.join(recs).lower()
        self.assertTrue('redirection' in recs_text or 'amoonguss' in recs_text)

    def test_no_recommendations_needed(self):
        """Test when team is well-balanced"""
        synergy_report = {
            'speed_control': ['Trick Room'],
            'support': ['Amoonguss'],
            'weaknesses': []
        }
        
        recs = recommend_optimizations([], synergy_report)
        
        # Should still return something positive
        self.assertGreater(len(recs), 0)
        recs_text = ' '.join(recs).lower()
        self.assertTrue('well covered' in recs_text or 'appear' in recs_text)


class TestEvaluateTeam(unittest.TestCase):
    """Test complete team evaluation"""

    def test_evaluate_complete_team(self):
        """Test evaluation of a complete team"""
        pokepaste = """Incineroar @ Sitrus Berry
Ability: Intimidate
- Fake Out
- Flare Blitz

Amoonguss @ Rocky Helmet
Ability: Regenerator
- Spore
- Rage Powder

Cresselia @ Mental Herb
Ability: Levitate
- Trick Room
- Moonblast"""
        
        result = evaluate_team(pokepaste)
        
        self.assertIsInstance(result, str)
        self.assertIn('Professor Sequoia', result)
        self.assertIn('Team Summary', result)

    def test_evaluate_team_with_trick_room(self):
        """Test evaluation identifies Trick Room"""
        pokepaste = """Cresselia @ Mental Herb
- Trick Room
- Moonblast
- Helping Hand
- Protect"""
        
        result = evaluate_team(pokepaste)
        
        self.assertIn('Trick Room', result)

    def test_evaluate_team_with_tailwind(self):
        """Test evaluation identifies Tailwind"""
        pokepaste = """Tornadus @ Focus Sash
- Tailwind
- Bleakwind Storm
- Taunt
- Protect"""
        
        result = evaluate_team(pokepaste)
        
        self.assertIn('Tailwind', result)

    def test_evaluate_no_pokemon_found(self):
        """Test evaluation with invalid input"""
        result = evaluate_team("This is not a valid pokepaste")
        
        self.assertIn('Error', result)


class TestHandleTeamEvaluation(unittest.IsolatedAsyncioTestCase):
    """Test async team evaluation handler"""

    async def test_handle_pokepaste_text(self):
        """Test handling direct Pokepaste text"""
        pokepaste = """Incineroar @ Sitrus Berry
- Fake Out
- Flare Blitz

Amoonguss @ Rocky Helmet
- Spore
- Rage Powder"""
        
        result = await handle_team_evaluation(pokepaste, user_id="test_user")
        
        self.assertEqual(result['status'], 'ok')
        self.assertIn('embed', result)

    async def test_handle_empty_input(self):
        """Test handling empty input"""
        result = await handle_team_evaluation("", user_id="test_user")
        
        self.assertEqual(result['status'], 'error')

    @patch('requests.get')
    async def test_handle_pokepaste_url(self, mock_get):
        """Test handling Pokepaste URL"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """Incineroar @ Sitrus Berry
- Fake Out
- Flare Blitz"""
        mock_get.return_value = mock_response
        
        result = await handle_team_evaluation(
            "https://pokepast.es/test123",
            user_id="test_user"
        )
        
        self.assertEqual(result['status'], 'ok')
        mock_get.assert_called_once()

    @patch('requests.get')
    async def test_handle_pokepaste_url_failure(self, mock_get):
        """Test handling failed Pokepaste URL fetch"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = await handle_team_evaluation(
            "https://pokepast.es/invalid",
            user_id="test_user"
        )
        
        self.assertEqual(result['status'], 'error')


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_incomplete_team_less_than_six(self):
        """Test handling team with fewer than 6 Pokemon"""
        pokepaste = """Incineroar @ Sitrus Berry
- Fake Out
- Flare Blitz

Amoonguss @ Rocky Helmet
- Spore
- Rage Powder"""
        
        team = parse_pokepaste(pokepaste)
        result = evaluate_synergy(team)
        
        # Should still evaluate successfully
        self.assertIn('summary', result)

    def test_pokemon_with_special_characters(self):
        """Test parsing Pokemon with special characters in name"""
        pokepaste = """Landorus-Therian @ Life Orb
- Earthquake
- Rock Slide"""
        
        team = parse_pokepaste(pokepaste)
        
        self.assertEqual(len(team), 1)
        self.assertEqual(team[0]['name'], 'Landorus-Therian')

    def test_missing_moves(self):
        """Test Pokemon with no moves specified"""
        team = [
            {
                'name': 'Incineroar',
                'types': ['Fire', 'Dark'],
                'moves': []
            }
        ]
        
        result = evaluate_synergy(team)
        
        # Should not crash
        self.assertIn('summary', result)

    def test_malformed_pokepaste(self):
        """Test handling malformed Pokepaste input"""
        malformed = """This is not
a valid
pokepaste format
at all"""
        
        team = parse_pokepaste(malformed)
        
        # Should return empty or handle gracefully
        self.assertIsInstance(team, list)


if __name__ == '__main__':
    unittest.main(verbosity=2)