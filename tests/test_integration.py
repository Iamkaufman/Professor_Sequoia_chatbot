"""
Integration tests for end-to-end functionality
"""

import unittest
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.controller import handle_buildcore_request


class TestEndToEnd(unittest.TestCase):
    """End-to-end integration tests"""

    def test_complete_workflow(self):
        """Test complete workflow from input to team generation"""
        # User requests a team
        result = asyncio.run(
            handle_buildcore_request(
                "Incineroar, Rillaboom",
                "integration_test_user",
                regulation="H"
            )
        )
        
        # Verify successful generation
        self.assertEqual(result['status'], 'ok')
        self.assertIn('team', result)
        self.assertEqual(len(result['team']), 6)
        
        # Verify team quality
        for pokemon in result['team']:
            # Has required fields
            self.assertIn('name', pokemon)
            self.assertIn('suggested_moves', pokemon)
            self.assertIn('suggested_item', pokemon)
            self.assertIn('suggested_ev', pokemon)
            
            # Moves are reasonable
            self.assertGreater(len(pokemon['suggested_moves']), 0)
            self.assertLessEqual(len(pokemon['suggested_moves']), 4)
            
            # No placeholder/invalid moves
            for move in pokemon['suggested_moves']:
                self.assertNotIn('hyper-beam', move.lower())
                self.assertNotIn('giga-impact', move.lower())

    def test_error_recovery(self):
        """Test system handles errors gracefully"""
        # Invalid input should not crash
        result = asyncio.run(
            handle_buildcore_request(
                "asdfghjkl",  # Gibberish
                "test_user",
                regulation="H"
            )
        )
        
        # Should return clarification or error, not crash
        self.assertIn(result['status'], ['error', 'clarify'])
        self.assertIsInstance(result['message'], str)


if __name__ == '__main__':
    unittest.main(verbosity=2)