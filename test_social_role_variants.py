#!/usr/bin/env python3
"""
Test script for the social role variant system.

This script tests:
1. VariantsManager functionality
2. World Configurator integration
3. NPCCreator service type integration
4. Export/import pipeline integrity
"""

import os
import sys
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))
# Add world_configurator to the path for internal imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'world_configurator'))

try:
    from world_configurator.models.variants_manager import VariantsManager
    from world_configurator.models.world_config import WorldConfigManager
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Import error: {e}")
    logger.info("This test requires the world_configurator package to be properly set up")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_variants_manager():
    """Test the VariantsManager functionality."""
    logger.info("=== Testing VariantsManager ===")
    
    manager = VariantsManager()
    
    # Test loading from existing variants.json
    variants_path = os.path.join(os.path.dirname(__file__), "config", "npc", "variants.json")
    if os.path.exists(variants_path):
        success = manager.load_from_file(variants_path)
        logger.info(f"Load from file: {'SUCCESS' if success else 'FAILED'}")
        
        if success:
            variants = manager.data.get("variants", {})
            logger.info(f"Loaded {len(variants)} variants")
            
            # Test filtering by social role
            guards = manager.get_social_role_variants("guard")
            officials = manager.get_social_role_variants("official")
            scholars = manager.get_social_role_variants("scholar")
            
            logger.info(f"Found {len(guards)} guard variants")
            logger.info(f"Found {len(officials)} official variants")
            logger.info(f"Found {len(scholars)} scholar variants")
            
            # Test filtering by culture
            concordant = manager.get_culture_variants("concordant")
            verdant = manager.get_culture_variants("verdant")
            
            logger.info(f"Found {len(concordant)} concordant variants")
            logger.info(f"Found {len(verdant)} verdant variants")
            
            # Test validation
            errors = []
            for variant_id, variant_data in variants.items():
                variant_errors = manager.validate_variant(variant_data)
                if variant_errors:
                    errors.extend([f"{variant_id}: {err}" for err in variant_errors])
            
            logger.info(f"Validation: {len(errors)} errors found")
            if errors:
                for error in errors[:5]:  # Show first 5 errors
                    logger.warning(f"  {error}")
    
    # Test creating a new social role variant
    try:
        variant_id = manager.create_social_role_variant(
            culture="test",
            role="guard",
            family_id="test_family",
            name="Test Guard",
            description="A test guard variant"
        )
        logger.info(f"Created test variant: {variant_id}")
        
        # Validate the created variant
        variant_data = manager.get_variant(variant_id)
        if variant_data:
            errors = manager.validate_variant(variant_data)
            logger.info(f"Test variant validation: {'PASSED' if not errors else 'FAILED'}")
        
        # Remove the test variant
        manager.remove_variant(variant_id)
        logger.info(f"Removed test variant: {variant_id}")
        
    except Exception as e:
        logger.error(f"Error testing variant creation: {e}")

def test_world_config_integration():
    """Test WorldConfigManager integration with variants."""
    logger.info("=== Testing WorldConfigManager Integration ===")
    
    try:
        world_config = WorldConfigManager()
        
        # Check if variants manager is present
        if hasattr(world_config, 'variants_manager'):
            logger.info("VariantsManager is properly integrated into WorldConfigManager")
            
            # Test loading
            variants_path = os.path.join(os.path.dirname(__file__), "config", "npc", "variants.json")
            if os.path.exists(variants_path):
                success = world_config.variants_manager.load_from_file(variants_path)
                logger.info(f"Load via WorldConfigManager: {'SUCCESS' if success else 'FAILED'}")
            
            # Check if it's in the managers map
            if "variants" in world_config.managers:
                logger.info("Variants manager is in the managers map")
            else:
                logger.warning("Variants manager is NOT in the managers map")
        else:
            logger.error("VariantsManager is NOT integrated into WorldConfigManager")
            
    except Exception as e:
        logger.error(f"Error testing WorldConfigManager integration: {e}")

def test_npc_creator_integration():
    """Test NPCCreator service type integration."""
    logger.info("=== Testing NPCCreator Integration ===")
    
    try:
        # This would require setting up the full game engine context
        # For now, just check if the code would work by importing
        from core.character.npc_creator import NPCCreator
        from core.base.config import get_config
        
        logger.info("NPCCreator import successful")
        
        # Check if the enhanced code exists
        creator = NPCCreator()
        if hasattr(creator, '_apply_variant_to_npc'):
            logger.info("NPCCreator has _apply_variant_to_npc method")
        else:
            logger.warning("NPCCreator is missing _apply_variant_to_npc method")
        
        logger.info("NPCCreator integration check completed")
        
    except Exception as e:
        logger.error(f"Error testing NPCCreator integration: {e}")

def test_export_import():
    """Test export/import functionality."""
    logger.info("=== Testing Export/Import ===")
    
    try:
        manager = VariantsManager()
        
        # Create a test variant
        variant_id = manager.create_social_role_variant(
            culture="test",
            role="official",
            family_id="test_family",
            name="Test Official",
            description="A test official variant"
        )
        
        # Test saving to a temp file
        temp_path = os.path.join(os.path.dirname(__file__), "temp_variants_test.json")
        success = manager.save_to_file(temp_path)
        logger.info(f"Save to temp file: {'SUCCESS' if success else 'FAILED'}")
        
        if success and os.path.exists(temp_path):
            # Test loading from temp file
            manager2 = VariantsManager()
            load_success = manager2.load_from_file(temp_path)
            logger.info(f"Load from temp file: {'SUCCESS' if load_success else 'FAILED'}")
            
            if load_success:
                # Check if our test variant is there
                loaded_variant = manager2.get_variant(variant_id)
                if loaded_variant:
                    logger.info("Test variant successfully saved and loaded")
                else:
                    logger.error("Test variant not found after save/load")
            
            # Clean up
            try:
                os.remove(temp_path)
                logger.info("Cleaned up temp file")
            except:
                pass
        
    except Exception as e:
        logger.error(f"Error testing export/import: {e}")

def main():
    """Run all tests."""
    logger.info("Starting Social Role Variant System Tests")
    
    try:
        test_variants_manager()
        test_world_config_integration()
        test_npc_creator_integration()
        test_export_import()
        
        logger.info("=== All Tests Completed ===")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")

if __name__ == "__main__":
    main()
