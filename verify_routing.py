import sys
import os
import math
from unittest.mock import MagicMock, patch

# Add the project root to sys.path
sys.path.append(os.getcwd())

# Avoid top-level imports that might cause circularity
from core.interaction.enums import InteractionMode
from core.base.commands import CommandResult, get_command_processor

def setup_mock_game():
    # Setup a minimal game environment for testing commands
    mock_engine = MagicMock()
    mock_state = MagicMock()
    mock_player = MagicMock()
    mock_player.name = "TestPlayer"
    mock_player.level = 1
    mock_player.race = "Human"
    mock_player.path = "Wanderer"
    mock_player.hp = 10.0
    mock_player.mana = 10.0
    mock_player.stamina = 10.0
    
    mock_state.player = mock_player
    mock_state.current_mode = InteractionMode.NARRATIVE
    mock_engine._state_manager.current_state = mock_state
    mock_engine._use_llm = True
    
    # Mock StatsManager
    mock_stats_mgr = MagicMock()
    mock_stats_mgr.get_stat_value.return_value = 10.0
    
    with patch('core.stats.stats_manager.get_stats_manager', return_value=mock_stats_mgr):
        # This will be used during execution
        pass
    
    # Mock output
    mock_engine._output = MagicMock()
    
    return mock_engine, mock_state

def test_command_processor_registration():
    print("--- Testing CommandProcessor Registration ---")
    mock_engine, mock_state = setup_mock_game()
    
    # Trigger registrations via engine initialization (simulated)
    try:
        from core.inventory.inventory_commands import register_inventory_commands
        from core.testing.quest_commands import register_quest_commands
        from core.stats.stats_commands import register_stats_commands
        
        register_inventory_commands()
        register_quest_commands()
        register_stats_commands()
    except Exception as e:
        print(f"Registration failed: {e}")
        return False
    
    cp = get_command_processor()
    
    commands_to_test = ["status", "stats", "GET_STATS", "inventory", "GET_INVENTORY", "quests", "GET_QUESTS"]
    
    all_pass = True
    for cmd in commands_to_test:
        name_low = cmd.lower()
        if name_low in cp._handlers or name_low in cp._aliases:
            print(f"CHECK: '{cmd}' is registered. [OK]")
        else:
            print(f"CHECK: '{cmd}' is MISSING! [FAIL]")
            all_pass = False
    
    return all_pass

def test_input_router_logic():
    print("\n--- Testing InputRouter Decision Logic ---")
    mock_engine, mock_state = setup_mock_game()
    
    # Mock Intent Sentinel
    mock_sentinel = MagicMock()
    mock_engine._agent_manager._intent_sentinel = mock_sentinel
    
    from core.game_flow.input_router import InputRouter
    router = InputRouter()
    
    test_cases = [
        ("I check my inventory", "STATUS", 0.9, "inventory"),
        ("Show my stats", "STATUS", 0.9, "status"),
        ("What are my quests?", "STATUS", 0.9, "quests"),
    ]
    
    all_pass = True
    for input_text, intent, confidence, expected_cmd in test_cases:
        mock_sentinel.classify.return_value = {"intent": intent, "confidence": confidence}
        
        with patch.object(router, '_process_direct_command') as mock_process:
            mock_process.return_value = CommandResult.success("Routing worked!")
            router.route_input(mock_engine, input_text)
            
            try:
                mock_process.assert_called_once_with(mock_engine, mock_state, expected_cmd)
                print(f"BYPASS: '{input_text}' -> '{expected_cmd}' [OK]")
            except AssertionError:
                actual_call = mock_process.call_args[0][2] if mock_process.called else "None"
                print(f"BYPASS: '{input_text}' failed! (Expected '{expected_cmd}', got '{actual_call}') [FAIL]")
                all_pass = False
                
    return all_pass

def test_status_command_execution():
    print("\n--- Testing Status Command Execution ---")
    mock_engine, mock_state = setup_mock_game()
    
    # Ensure player vitals are definitely floats
    mock_state.player.hp = 10.0
    mock_state.player.mana = 10.0
    mock_state.player.stamina = 10.0
    mock_state.player.level = 1
    
    cp = get_command_processor()
    
    # Mock StatsManager to return floats
    mock_stats_mgr = MagicMock()
    mock_stats_mgr.get_stat_value.return_value = 100.0
    
    with patch('core.stats.stats_manager.get_stats_manager', return_value=mock_stats_mgr):
        result = cp.process_command(mock_state, "status")
    
    if result and result.status.name == "SUCCESS":
        print("EXEC: 'status' executed successfully.")
        print("Output Preview:")
        print("-" * 20)
        print(result.message[:200] + "...")
        print("-" * 20)
        return True
    else:
        msg = result.message if result else "No result"
        print(f"EXEC: 'status' failed: {msg} [FAIL]")
        return False

if __name__ == "__main__":
    p1 = test_command_processor_registration()
    p2 = test_input_router_logic()
    p3 = test_status_command_execution()
    
    if p1 and p2 and p3:
        print("\nALL VERIFICATIONS PASSED!")
        sys.exit(0)
    else:
        print("\nVERIFICATION FAILED!")
        sys.exit(1)
