
import os
import sys
import logging
from core.base.state.state_manager import get_state_manager
from core.character.npc_base import NPCType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TEST")

def test_npc_persistence():
    logger.info("Starting NPC Persistence Test")
    
    # 1. Get State Manager and NPC System
    state_manager = get_state_manager()
    npc_system = state_manager.get_npc_system()
    
    if not npc_system:
        logger.error("Failed to get NPCSystem")
        return
        
    logger.info(f"NPC System obtained. Manager ID: {id(npc_system.manager)}")
    
    # 2. Create an enemy
    logger.info("Creating enemy...")
    enemy = npc_system.create_enemy_for_combat(
        name="Test Bandit",
        enemy_type="bandit",
        level=1,
        location="Test Location"
    )
    
    if not enemy:
        logger.error("Failed to create enemy")
        return
        
    logger.info(f"Created enemy: {enemy.name} (ID: {enemy.id})")
    
    # 3. Verify it's in the manager
    in_manager = npc_system.get_npc(enemy.id)
    if in_manager:
        logger.info("Enemy found in NPCManager")
    else:
        logger.error("Enemy NOT found in NPCManager immediately after creation!")
        
    # 4. Verify persistence flag
    logger.info(f"Is persistent: {enemy.is_persistent}")
    if not enemy.is_persistent:
        logger.error("Enemy is NOT marked as persistent! This is the bug.")
        # Manually fix for test if needed, but we want to see if it fails
    
    # 5. Save state
    logger.info("Saving NPC system state...")
    success = npc_system.save_state()
    logger.info(f"Save result: {success}")
    
    # 6. Check file existence
    save_path = os.path.join("saves", "npcs", f"{enemy.id}.json")
    if os.path.exists(save_path):
        logger.info(f"SUCCESS: File exists at {save_path}")
        # Clean up
        os.remove(save_path)
        logger.info("Test file cleaned up")
    else:
        logger.error(f"FAILURE: File does NOT exist at {save_path}")
        
    # 7. Check save directory
    save_dir = "saves/npcs"
    if os.path.exists(save_dir):
        logger.info(f"Save directory exists: {save_dir}")
        logger.info(f"Contents: {os.listdir(save_dir)}")
    else:
        logger.error(f"Save directory does not exist: {save_dir}")

if __name__ == "__main__":
    test_npc_persistence()
