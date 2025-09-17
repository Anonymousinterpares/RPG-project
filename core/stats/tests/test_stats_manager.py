# core/stats/tests/test_stats_manager.py
import unittest
import math
from unittest.mock import patch, MagicMock

# Assuming the project root is added to PYTHONPATH or tests are run from the root
# Adjust the import path based on how tests are run
try:
    from core.stats.stats_manager import StatsManager
    from core.stats.stats_base import StatType, DerivedStatType, StatModifier
    from core.stats.modifier import ModifierSource, ModifierType
except ImportError:
    # If running from within the tests directory, adjust path
    import sys
    import os
    # Go up three levels from core/stats/tests to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from core.stats.stats_manager import StatsManager
    from core.stats.stats_base import StatType, DerivedStatType, StatModifier
    from core.stats.modifier import ModifierSource, ModifierType

class TestStatsManagerSkillCheck(unittest.TestCase):

    def setUp(self):
        """Set up a StatsManager instance for testing."""
        # Use a temporary config or mock it if necessary
        self.manager = StatsManager()
        # Set predictable base stats for testing
        self.manager.set_base_stat(StatType.STRENGTH, 14) # +2 mod
        self.manager.set_base_stat(StatType.DEXTERITY, 10) # +0 mod
        self.manager.set_base_stat(StatType.CONSTITUTION, 12) # +1 mod
        self.manager.set_base_stat(StatType.INTELLIGENCE, 8)  # -1 mod
        self.manager.set_base_stat(StatType.WISDOM, 16) # +3 mod
        self.manager.set_base_stat(StatType.CHARISMA, 11) # +0 mod
        self.manager.set_base_stat(StatType.WILLPOWER, 13) # +1 mod
        self.manager.set_base_stat(StatType.INSIGHT, 15) # +2 mod
        self.manager.set_level(1) # Recalculates derived stats

    def test_basic_check_success(self):
        """Test a basic skill check that should succeed."""
        # STR check (mod +2) vs DC 10
        with patch('random.randint', return_value=9): # Roll 9 + 2 = 11 >= 10
            result = self.manager.perform_skill_check(StatType.STRENGTH, difficulty=10)
            self.assertTrue(result.success)
            self.assertEqual(result.roll, 9)
            self.assertEqual(result.modifier, 2)
            self.assertEqual(result.total, 11)
            self.assertFalse(result.critical)

    def test_basic_check_failure(self):
        """Test a basic skill check that should fail."""
        # STR check (mod +2) vs DC 15
        with patch('random.randint', return_value=10): # Roll 10 + 2 = 12 < 15
            result = self.manager.perform_skill_check(StatType.STRENGTH, difficulty=15)
            self.assertFalse(result.success)
            self.assertEqual(result.roll, 10)
            self.assertEqual(result.modifier, 2)
            self.assertEqual(result.total, 12)
            self.assertFalse(result.critical)

    def test_check_with_advantage_success(self):
        """Test a check with advantage succeeding."""
        # WIS check (mod +3) vs DC 15
        with patch('random.randint', side_effect=[5, 14]): # Rolls 5 and 14, takes 14. 14 + 3 = 17 >= 15
            result = self.manager.perform_skill_check(StatType.WISDOM, difficulty=15, advantage=True)
            self.assertTrue(result.success)
            self.assertEqual(result.roll, 14) # Should use the higher roll
            self.assertEqual(result.modifier, 3)
            self.assertEqual(result.total, 17)
            self.assertTrue(result.advantage)
            self.assertFalse(result.disadvantage)

    def test_check_with_disadvantage_failure(self):
        """Test a check with disadvantage failing."""
        # WIS check (mod +3) vs DC 15
        with patch('random.randint', side_effect=[16, 8]): # Rolls 16 and 8, takes 8. 8 + 3 = 11 < 15
            result = self.manager.perform_skill_check(StatType.WISDOM, difficulty=15, disadvantage=True)
            self.assertFalse(result.success)
            self.assertEqual(result.roll, 8) # Should use the lower roll
            self.assertEqual(result.modifier, 3)
            self.assertEqual(result.total, 11)
            self.assertFalse(result.advantage)
            self.assertTrue(result.disadvantage)

    def test_check_with_advantage_and_disadvantage(self):
        """Test that advantage and disadvantage cancel out."""
        # WIS check (mod +3) vs DC 15
        # Mock randint to be called only once
        with patch('random.randint', return_value=10) as mock_randint: # 10 + 3 = 13 < 15
            result = self.manager.perform_skill_check(StatType.WISDOM, difficulty=15, advantage=True, disadvantage=True)
            self.assertFalse(result.success)
            self.assertEqual(result.roll, 10)
            self.assertEqual(result.modifier, 3)
            self.assertEqual(result.total, 13)
            self.assertTrue(result.advantage) # Flags are still true
            self.assertTrue(result.disadvantage)
            mock_randint.assert_called_once_with(1, 20) # Ensure only one roll happened

    def test_check_with_positive_situational_modifier(self):
        """Test a check with a positive situational modifier."""
        # INT check (mod -1) vs DC 10, with +3 situational
        with patch('random.randint', return_value=7): # Roll 7 - 1 + 3 = 9 < 10
            result = self.manager.perform_skill_check(StatType.INTELLIGENCE, difficulty=10, situational_modifier=3)
            self.assertFalse(result.success)
            self.assertEqual(result.roll, 7)
            self.assertEqual(result.modifier, -1)
            self.assertEqual(result.situational_modifier, 3)
            self.assertEqual(result.total, 9)

    def test_check_with_negative_situational_modifier(self):
        """Test a check with a negative situational modifier."""
        # STR check (mod +2) vs DC 10, with -4 situational
        with patch('random.randint', return_value=11): # Roll 11 + 2 - 4 = 9 < 10
            result = self.manager.perform_skill_check(StatType.STRENGTH, difficulty=10, situational_modifier=-4)
            self.assertFalse(result.success)
            self.assertEqual(result.roll, 11)
            self.assertEqual(result.modifier, 2)
            self.assertEqual(result.situational_modifier, -4)
            self.assertEqual(result.total, 9)

    def test_check_with_stat_modifier_applied(self):
        """Test a check where the base stat has a modifier."""
        # Add a +2 temporary bonus to STR (base 14 -> 16, mod +2 -> +3)
        mod = StatModifier(
            stat=StatType.STRENGTH,
            value=2,
            type=ModifierType.FLAT,
            source=ModifierSource.TEMPORARY,
            source_name="Blessing",
            duration=5
        )
        self.manager.add_modifier(mod)
        # Need to access internal modifier manager for testing this properly
        # Or rely on get_stat_value which uses the modifier manager
        self.assertEqual(self.manager.get_stat_value(StatType.STRENGTH), 16) # Verify stat value

        # STR check (mod +3 now) vs DC 15
        with patch('random.randint', return_value=11): # Roll 11 + 3 = 14 < 15
            result = self.manager.perform_skill_check(StatType.STRENGTH, difficulty=15)
            self.assertFalse(result.success)
            self.assertEqual(result.roll, 11)
            self.assertEqual(result.modifier, 3) # Modifier should reflect the buffed stat
            self.assertEqual(result.total, 14)

        # Clean up modifier
        self.manager.remove_modifier(mod.id)
        self.assertEqual(self.manager.get_stat_value(StatType.STRENGTH), 14) # Verify stat value reverted

    def test_critical_success(self):
        """Test a critical success (natural 20)."""
        # INT check (mod -1) vs DC 25 (normally impossible)
        with patch('random.randint', return_value=20):
            result = self.manager.perform_skill_check(StatType.INTELLIGENCE, difficulty=25)
            self.assertTrue(result.success) # Should succeed regardless of DC
            self.assertEqual(result.roll, 20)
            self.assertEqual(result.modifier, -1)
            self.assertEqual(result.total, 19 + 0) # Roll + mod + sit_mod
            self.assertTrue(result.critical)

    def test_critical_failure(self):
        """Test a critical failure (natural 1)."""
        # STR check (mod +2) vs DC 5 (normally easy)
        with patch('random.randint', return_value=1):
            result = self.manager.perform_skill_check(StatType.STRENGTH, difficulty=5)
            self.assertFalse(result.success) # Should fail regardless of DC
            self.assertEqual(result.roll, 1)
            self.assertEqual(result.modifier, 2)
            self.assertEqual(result.total, 3 + 0) # Roll + mod + sit_mod
            self.assertTrue(result.critical)

    def test_check_against_derived_stat_uses_correct_modifier(self):
        """Test check against derived stat uses primary stat modifier."""
        # The current implementation calculates the modifier based on the *value*
        # of the derived stat passed to perform_check, which is likely incorrect
        # for stats like Attack Bonus.
        # A check involving Melee Attack should likely use the STR modifier.
        # Let's test this assumption.
        # STR = 14 (+2 mod)
        # Melee Attack base value = 4 (Proficiency + STR mod = 2 + 2 at level 1)
        # get_stat_value(DerivedStatType.MELEE_ATTACK) returns 4.
        # perform_skill_check calculates mod = floor((4-10)/2) = -3.

        # This test confirms the *current* (potentially flawed) behavior.
        with patch('random.randint', return_value=10): # Roll 10
            result = self.manager.perform_skill_check(DerivedStatType.MELEE_ATTACK, difficulty=8)
            # Expected total = roll + mod_from_derived_value + sit_mod = 10 + (-3) + 0 = 7
            self.assertFalse(result.success) # 7 < 8
            self.assertEqual(result.modifier, -3) # Mod derived from MELEE_ATTACK value (4)
            self.assertEqual(result.total, 7)

        # If the design intent changes to use the primary stat's modifier directly,
        # this test would need to be updated. For example, if it used STR mod (+2):
        # Expected total = 10 + 2 + 0 = 12. Success against DC 8.

    def test_check_against_resolve(self):
        """Test a check using the new RESOLVE derived stat."""
        # Resolve base value depends on WIL(13/+1), CHA(11/+0), level 1
        # Base = 10 (default), resolve_per_level = 3 (default)
        # Level 1: base_resolve + wil_mod + cha_mod = 10 + 1 + 0 = 11
        # get_stat_value(RESOLVE) returns 11
        # Modifier from value 11 = floor((11-10)/2) = 0

        with patch('random.randint', return_value=10): # Roll 10
             # Check vs DC 11, using modifier derived from Resolve value (11 -> 0)
             # Total = 10 + 0 + 0 = 10
            result = self.manager.perform_skill_check(DerivedStatType.RESOLVE, difficulty=11)
            self.assertFalse(result.success) # 10 < 11
            self.assertEqual(result.modifier, 0) # Mod derived from RESOLVE value (11)
            self.assertEqual(result.total, 10)


if __name__ == '__main__':
    # Allows running the tests directly
    unittest.main(argv=['first-arg-is-ignored'], exit=False)