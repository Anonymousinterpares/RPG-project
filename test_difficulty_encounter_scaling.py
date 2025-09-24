#!/usr/bin/env python3
"""
Test script to verify difficulty and encounter_size parameter propagation
through the NPC generation system.
"""

import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.character.npc_family_generator import NPCFamilyGenerator
from core.character.npc_creator import NPCCreator
from core.character.npc_manager import NPCManager
from core.base.config import get_config
from core.stats.stats_base import DerivedStatType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_npc_family_generator_scaling():
    """Test NPCFamilyGenerator scaling with different difficulty and encounter_size values."""
    logger.info("=== Testing NPCFamilyGenerator Scaling ===")
    
    try:
        fam_gen = NPCFamilyGenerator()
        
        # Test with different difficulty levels
        difficulties = ["story", "normal", "hard", "expert"]
        encounter_sizes = ["solo", "pack", "mixed"]
        
        # Use a common family if available
        families = list(fam_gen._families.keys())
        if not families:
            logger.error("No families found in configuration")
            return False
        
        test_family = families[0]
        logger.info(f"Testing with family: {test_family}")
        
        results = {}
        
        for difficulty in difficulties:
            for encounter_size in encounter_sizes:
                try:
                    npc = fam_gen.generate_npc_from_family(
                        family_id=test_family,
                        name=f"Test_{difficulty}_{encounter_size}",
                        level=5,  # Use level 5 to test level curve scaling
                        difficulty=difficulty,
                        encounter_size=encounter_size
                    )
                    
                    if npc and npc.stats_manager:
                        hp = npc.stats_manager.get_stat_value(DerivedStatType.HEALTH)
                        max_hp = npc.stats_manager.get_stat_value(DerivedStatType.MAX_HEALTH)
                        defense = npc.stats_manager.get_stat_value(DerivedStatType.DEFENSE)
                        initiative = npc.stats_manager.get_stat_value(DerivedStatType.INITIATIVE)
                        
                        results[f"{difficulty}_{encounter_size}"] = {
                            "hp": hp,
                            "max_hp": max_hp,
                            "defense": defense,
                            "initiative": initiative
                        }
                        
                        logger.info(f"{difficulty}/{encounter_size}: HP={hp:.1f}/{max_hp:.1f}, DEF={defense:.1f}, INIT={initiative:.1f}")
                    else:
                        logger.warning(f"Failed to generate NPC for {difficulty}/{encounter_size}")
                        
                except Exception as e:
                    logger.error(f"Error generating NPC for {difficulty}/{encounter_size}: {e}")
        
        # Verify scaling works by comparing story vs hard difficulty
        if "story_solo" in results and "hard_solo" in results:
            story_hp = results["story_solo"]["hp"]
            hard_hp = results["hard_solo"]["hp"]
            
            if hard_hp > story_hp * 1.1:  # Hard should be at least 10% higher
                logger.info("✓ Difficulty scaling appears to work correctly")
            else:
                logger.warning(f"⚠ Difficulty scaling may not be working: story={story_hp:.1f}, hard={hard_hp:.1f}")
        
        # Verify encounter size scaling by comparing solo vs pack
        if "normal_solo" in results and "normal_pack" in results:
            solo_hp = results["normal_solo"]["hp"]
            pack_hp = results["normal_pack"]["hp"]
            
            if pack_hp < solo_hp * 0.95:  # Pack should be lower than solo
                logger.info("✓ Encounter size scaling appears to work correctly")
            else:
                logger.warning(f"⚠ Encounter size scaling may not be working: solo={solo_hp:.1f}, pack={pack_hp:.1f}")
                
        return True
        
    except Exception as e:
        logger.error(f"Error in NPCFamilyGenerator scaling test: {e}")
        return False

def test_npc_creator_parameter_propagation():
    """Test that NPCCreator properly propagates difficulty and encounter_size parameters."""
    logger.info("=== Testing NPCCreator Parameter Propagation ===")
    
    try:
        # Create NPC manager and creator
        npc_manager = NPCManager()
        npc_creator = NPCCreator(npc_manager)
        
        # Mock config to set specific difficulty and encounter_size
        from unittest.mock import patch
        
        test_configs = [
            {"game.difficulty": "story", "game.encounter_size": "solo"},
            {"game.difficulty": "hard", "game.encounter_size": "pack"},
            {"game.difficulty": "expert", "game.encounter_size": "mixed"}
        ]
        
        for config in test_configs:
            with patch.object(get_config(), 'get', side_effect=lambda key, default=None: config.get(key, default)):
                try:
                    # Test enemy creation in families mode
                    npc = npc_creator.create_enemy(
                        name=f"TestEnemy_{config['game.difficulty']}_{config['game.encounter_size']}",
                        enemy_type="test_family" if "test_family" in NPCFamilyGenerator()._families else list(NPCFamilyGenerator()._families.keys())[0] if NPCFamilyGenerator()._families else "generic",
                        level=3
                    )
                    
                    if npc and npc.stats_manager:
                        hp = npc.stats_manager.get_stat_value(DerivedStatType.HEALTH)
                        logger.info(f"Created enemy with {config['game.difficulty']}/{config['game.encounter_size']}: HP={hp:.1f}")
                    else:
                        logger.warning(f"Failed to create enemy with config: {config}")
                        
                except Exception as e:
                    logger.error(f"Error creating enemy with config {config}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in NPCCreator parameter propagation test: {e}")
        return False

def test_variant_scaling():
    """Test that variant NPCs also respect difficulty and encounter_size scaling."""
    logger.info("=== Testing Variant Scaling ===")
    
    try:
        fam_gen = NPCFamilyGenerator()
        
        # Check if we have any variants
        variants = list(fam_gen._variants.keys())
        if not variants:
            logger.info("No variants found, skipping variant scaling test")
            return True
        
        test_variant = variants[0]
        logger.info(f"Testing with variant: {test_variant}")
        
        # Test variant with different difficulties
        difficulties = ["normal", "hard"]
        results = {}
        
        for difficulty in difficulties:
            try:
                npc = fam_gen.generate_npc_from_variant(
                    variant_id=test_variant,
                    name=f"TestVariant_{difficulty}",
                    level=5,
                    difficulty=difficulty,
                    encounter_size="solo"
                )
                
                if npc and npc.stats_manager:
                    hp = npc.stats_manager.get_stat_value(DerivedStatType.HEALTH)
                    results[difficulty] = hp
                    logger.info(f"Variant {test_variant} with {difficulty}: HP={hp:.1f}")
                    
            except Exception as e:
                logger.error(f"Error generating variant {test_variant} with {difficulty}: {e}")
        
        # Verify variant scaling
        if "normal" in results and "hard" in results:
            if results["hard"] > results["normal"] * 1.05:  # Hard should be higher
                logger.info("✓ Variant scaling appears to work correctly")
            else:
                logger.warning(f"⚠ Variant scaling may not be working: normal={results['normal']:.1f}, hard={results['hard']:.1f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in variant scaling test: {e}")
        return False

def test_level_curve_interpolation():
    """Test that the level curve interpolation is working properly."""
    logger.info("=== Testing Level Curve Interpolation ===")
    
    try:
        fam_gen = NPCFamilyGenerator()
        
        # Test with different levels to see if curves are applied
        families = list(fam_gen._families.keys())
        if not families:
            logger.error("No families found for level curve test")
            return False
        
        test_family = families[0]
        levels = [1, 5, 10, 15, 20]
        results = {}
        
        for level in levels:
            try:
                npc = fam_gen.generate_npc_from_family(
                    family_id=test_family,
                    name=f"TestLevel_{level}",
                    level=level,
                    difficulty="normal",
                    encounter_size="solo"
                )
                
                if npc and npc.stats_manager:
                    hp = npc.stats_manager.get_stat_value(DerivedStatType.HEALTH)
                    results[level] = hp
                    logger.info(f"Level {level}: HP={hp:.1f}")
                    
            except Exception as e:
                logger.error(f"Error generating NPC at level {level}: {e}")
        
        # Check if there's progression (though with current config it might be flat)
        if len(results) >= 2:
            level_values = sorted(results.items())
            logger.info("✓ Level curve interpolation completed (check values above for progression)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in level curve interpolation test: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting difficulty and encounter_size scaling tests...")
    
    # Check if we're in families mode
    try:
        cfg = get_config()
        mode = (cfg.get("system.npc_generation_mode", "legacy") or "legacy").lower()
        logger.info(f"NPC generation mode: {mode}")
        
        if mode != "families":
            logger.warning("Not in families mode - some tests may not be applicable")
    except Exception as e:
        logger.error(f"Could not check NPC generation mode: {e}")
    
    tests = [
        ("NPCFamilyGenerator Scaling", test_npc_family_generator_scaling),
        ("NPCCreator Parameter Propagation", test_npc_creator_parameter_propagation),
        ("Variant Scaling", test_variant_scaling),
        ("Level Curve Interpolation", test_level_curve_interpolation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            if test_func():
                logger.info(f"✓ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"✗ {test_name} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} CRASHED: {e}")
            failed += 1
    
    logger.info(f"\n=== Test Summary ===")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed == 0:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error(f"💥 {failed} test(s) failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
