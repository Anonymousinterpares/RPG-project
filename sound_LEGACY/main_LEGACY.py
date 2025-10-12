#main.py
from pathlib import Path
import re
import sys
import asyncio
from queue import Queue
import os
from dataclasses import asdict
from typing import Optional
import uuid
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
from PySide6.QtCore import QTimer, QMetaObject, Qt, Q_ARG
from gui.message_widget import MessageWidget
from core.base.config import GameConfig
from core.base.state import StateManager
from core.base.commands import CommandProcessor
from core.base.command_result import CommandResult
from core.base.game_loop import GameLoop, GameSpeed
from core.utils.save_manager import SaveManager
from core.utils.logging_config import LoggingConfig
from core.llm.llm_manager import LLMManager
from core.memory.context_manager import ContextManager, ContextType
from core.agents.narrator import NarratorAgent
from core.agents.rule_checker import RuleCheckerAgent
from core.agents.context_evaluator import ContextEvaluatorAgent
from core.agents.base_agent import AgentContext
from core.utils.logging_config import LoggingConfig, LogCategory
from core.quest_manager import QuestManager
from core.inventory.item_manager import InventoryManager
from core.inventory.narrative_item_manager import NarrativeItemManager

class GameManager:
    def __init__(self):
        LoggingConfig.setup_logging()
        self.logger = LoggingConfig.get_logger(__name__, LogCategory.GAME)
        self.logger.info("GameManager initializing...")

        self.config = GameConfig()
        LoggingConfig.update_logging_level(self.config.settings.get("debug_mode", False))
        self.logger.debug("Config loaded with settings: %s", self.config.settings)
        
        try:
            self.logger.debug(f"Config settings after init: {self.config.settings}")
            
            # Initialize managers
            self.save_manager = SaveManager(self.config)
            self.state_manager = StateManager(self.config)
            self.state_manager.save_manager = self.save_manager
            
            # Initialize context manager
            memory_config = {
                "debug": self.config.settings.get("debug_mode", False),
                "memory_limits": {
                    "hot": 1000,
                    "warm": 2000,
                    "cold": 5000
                },
                "project_root": Path(self.config.project_root)
            }
            self.context_manager = ContextManager(memory_config)
            self.state_manager.context_manager = self.context_manager
            
            self.context_manager.logger.propagate = True
            print("ContextManager logger propagate:", self.context_manager.logger.propagate)

            # Initialize LLM Manager
            self.llm_manager = LLMManager(self.config)
            self.state_manager.llm_manager = self.llm_manager
            self.llm_manager.logger.propagate = True
            print("LLMManager logger propagate:", self.llm_manager.logger.propagate)

            # Initialize agents BEFORE command processor
            self.agents = {
                "narrator": NarratorAgent(self.config, self.llm_manager),
                "rule_checker": RuleCheckerAgent(self.config),
                "context_evaluator": ContextEvaluatorAgent(self.config, self.llm_manager)
            }
            
            # Initialize inventory and narrative item managers
            self.initialize_item_managers()

            # Connect the item_factory to the narrator agent
            if hasattr(self, 'narrative_item_manager') and hasattr(self.narrative_item_manager, 'item_factory'):
                if hasattr(self.agents["narrator"], 'set_item_factory'):
                    self.agents["narrator"].set_item_factory(self.narrative_item_manager.item_factory)
                    self.logger.info("Connected item_factory to narrator agent")

            # Set agents in state manager
            self.state_manager.agents = self.agents
            
            # Initialize quest manager

            self.quest_manager = QuestManager(self.state_manager)
            
            # Now initialize command processor
            self.command_processor = CommandProcessor(self.state_manager)
            
            self.game_loop = None
            self.input_queue = Queue()
            self.is_running = False
            
            self.current_api_token = uuid.uuid4().hex
            
            self.marked_for_deletion = []  # Files marked for deletion but not yet deleted
            self.deleted_saves = []        # Files that were deleted but can be restored
        
        except Exception as e:
            self.logger.error(f"Error initializing game manager: {str(e)}")
            raise

    def initialize_item_managers(self):
        """Initialize or connect to inventory and narrative item managers"""
        # Connect to state manager's inventory manager
        if hasattr(self.state_manager, 'inventory_manager'):
            self.inventory_manager = self.state_manager.inventory_manager
        else:
            # Create one if not exists

            self.inventory_manager = InventoryManager(self.config)
            self.state_manager.inventory_manager = self.inventory_manager
        
        # Connect to state manager's narrative item manager
        if hasattr(self.state_manager, 'narrative_item_manager'):
            self.narrative_item_manager = self.state_manager.narrative_item_manager
        else:
            # Create one if not exists
            self.narrative_item_manager = NarrativeItemManager(self.config, self.llm_manager, self.state_manager)
            self.state_manager.narrative_item_manager = self.narrative_item_manager

    def clear_current_game_context(self):
        """
        Fully resets the current game state and context.
        """
        # Cancel any pending API query
        if hasattr(self, "pending_api_task") and self.pending_api_task is not None:
            self.pending_api_task.cancel()
            self.pending_api_task = None
        
        import uuid
        self.current_api_token = uuid.uuid4().hex  # Update token so that any pending API call becomes outdated.
        
        # Reinitialize state manager
        from core.base.state import StateManager
        self.state_manager = StateManager(self.config)
        
        # Reinitialize managers
        from core.utils.save_manager import SaveManager
        self.save_manager = SaveManager(self.config)
        self.state_manager.save_manager = self.save_manager
        
        # Reinitialize context manager
        from core.memory.context_manager import ContextManager
        memory_config = {
            "debug": self.config.settings.get("debug_mode", False),
            "memory_limits": {
                "hot": 1000,
                "warm": 2000,
                "cold": 5000
            },
            "project_root": Path(self.config.project_root)
        }
        self.context_manager = ContextManager(memory_config)
        self.state_manager.context_manager = self.context_manager
        
        # Reinitialize agents
        from core.agents.narrator import NarratorAgent
        from core.agents.rule_checker import RuleCheckerAgent
        from core.agents.context_evaluator import ContextEvaluatorAgent
        
        self.agents = {
            "narrator": NarratorAgent(self.config, self.llm_manager),
            "rule_checker": RuleCheckerAgent(self.config),
            "context_evaluator": ContextEvaluatorAgent(self.config, self.llm_manager)
        }
        
        # Set agents in state manager
        self.state_manager.agents = self.agents
        
        # Reinitialize quest manager
        from core.quest_manager import QuestManager
        self.quest_manager = QuestManager(self.state_manager)
        
        # Reinitialize command processor
        from core.base.commands import CommandProcessor
        self.command_processor = CommandProcessor(self.state_manager)
        
        # Reset the game loop
        self.game_loop = None
        
        # Clear any existing game state
        self.state_manager.state = None
        
        # If GUI exists, clear its display panels
        if hasattr(self, "gui") and self.gui is not None:
            self.gui.conversationWidget.clearMessages()

    def cleanup_on_exit(self):
        """Clean up resources and perform final actions before exiting"""
        logger = LoggingConfig.get_logger(__name__, LogCategory.SYSTEM)
        logger.info("Performing cleanup on application exit")
        
        # Handle deleted saves
        try:
            # Execute final deletion of saves marked for deletion
            if hasattr(self, 'deleted_saves') and self.deleted_saves:
                logger.info(f"Permanently deleting {len(self.deleted_saves)} files marked for deletion")
                
                for deleted_info in self.deleted_saves:
                    try:
                        # Delete save file
                        save_path = Path(deleted_info.get('path', ''))
                        if save_path.exists():
                            save_path.unlink()
                            logger.debug(f"Deleted save file: {save_path}")
                        
                        # Delete memory file
                        memory_path = deleted_info.get('memory_path')
                        if memory_path:
                            memory_path = Path(memory_path)
                            if memory_path.exists():
                                memory_path.unlink()
                                logger.debug(f"Deleted memory file: {memory_path}")
                        
                    except Exception as e:
                        logger.error(f"Error deleting file during cleanup: {e}")
        except Exception as e:
            logger.error(f"Error in deletion cleanup: {e}")
        
        # Save any active game state only if autosave_on_exit is enabled AND game is properly initialized
        try:
            # Check if autosave_on_exit is enabled in config
            autosave_enabled = self.config.settings.get("autosave_on_exit", False)
            
            # Check if game state exists and is properly initialized with player data
            game_initialized = (
                hasattr(self, 'state_manager') and 
                self.state_manager.state and 
                hasattr(self.state_manager.state, 'player') and
                hasattr(self.state_manager.state.player, 'name') and
                self.state_manager.state.player.name
            )
            
            if autosave_enabled and game_initialized:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                exit_save_name = f"exit_save_{timestamp}"
                
                success, message = self.save_manager.create_save(
                    self.state_manager, exit_save_name, auto=True)
                    
                if success:
                    logger.info(f"Final exit save created: {exit_save_name}")
                else:
                    logger.error(f"Failed to create exit save: {message}")
            else:
                if not autosave_enabled:
                    logger.info("Autosave on exit is disabled - skipping exit save")
                elif not game_initialized:
                    logger.info("No initialized game found - skipping exit save")
        except Exception as e:
            logger.error(f"Error creating exit save: {e}")
        
        # Add any other cleanup needed
        logger.info("Cleanup completed")

    async def start_game(self, gui_input_queue: Optional[Queue] = None):

        if not self.state_manager.state:
            print("Failed to initialize game state")
            return
        self.game_loop = GameLoop(self.state_manager, self.command_processor)
        if gui_input_queue:
            self.game_loop.input_queue = gui_input_queue
        self.is_running = True
        try:
            await self.game_loop.start()
        except Exception as e:
            self.logger.error(f"Game loop error: {str(e)}", exc_info=True)
            success, _ = self.save_manager.create_save(self.state_manager, "emergency_save", auto=True)
            if success:
                print("Emergency save created successfully.")
            else:
                print("Failed to create emergency save.")
        finally:
            self.is_running = False
            print("\nThank you for playing!")
    
    def _load_game_with_filename(self, filename: str):
        """Load a saved game immediately using the provided filename."""
        try:
            # First, store the current game state temporarily in case load fails
            previous_state = self.state_manager.state
            
            success = self.state_manager.load_game(filename)
            if success:
                # Ensure player's state has 'path'
                if not hasattr(self.state_manager.state.player, 'path'):
                    background = self.state_manager.state.player.background
                    mapping = {
                        "concordat_scholar": "academic",
                        "failed_apprentice": "academic",
                        "archaeological_prodigy": "academic",
                        "crown_guard_veteran": "military",
                        "mercenary_mage": "military",
                        "reformed_artifact_smuggler": "criminal",
                        "guild_thief": "criminal",
                        "merchant_heir": "civilian",
                        "village_mystic": "civilian"
                    }
                    setattr(self.state_manager.state.player, 'path', mapping.get(background, "academic"))
                
                # Load memories for this game session
                if hasattr(self.state_manager, 'context_manager'):
                    self.state_manager.context_manager.current_session_id = self.state_manager.state.session_id
                    
                    # Use the save name without extension for memory loading
                    save_name = Path(filename).stem
                    
                    # Explicitly load memories for this session
                    success = self.state_manager.context_manager.load_memories_for_game(
                        self.state_manager.state.session_id, save_name)
                    
                    if success:
                        self.logger.info(f"Memories loaded successfully for session {self.state_manager.state.session_id}")
                    else:
                        self.logger.warning(f"Failed to load memories for session {self.state_manager.state.session_id}")
                
                # Initialize game loop with loaded state
                self.game_loop = GameLoop(self.state_manager, self.command_processor)
                self.is_running = True

                # Create the context for the summary request
                context = AgentContext(
                    current_location=self.state_manager.state.player.location,
                    game_state=asdict(self.state_manager.state),
                    conversation_history=self.state_manager.state.conversation_history,
                    active_quests=self.state_manager.state.active_quests,
                    context_manager=self.context_manager,
                    context_type="summary",
                    context_evaluator=self.agents.get("context_evaluator")
                )
                context.game_state["current_input"] = (
                    "Provide a detailed summary of the recent events and current game state "
                    "as a welcoming message for the loaded game. DO NOT include detailed character statistics, "
                    "attribute values, or derived stats in your response as these are already displayed in the "
                    "game interface. Focus instead on narrative elements, location description, and atmosphere."
                )

                # Add quest information to context - ADD THIS PART
                if hasattr(self, 'quest_manager'):
                    quest_summary = self.quest_manager.get_active_quests_summary()
                    context.game_state["quest_summary"] = quest_summary

                narrator_agent = self.agents.get("narrator")
                try:
                    loop = self.loop
                except Exception:
                    loop = asyncio.get_event_loop()

                # Capture the current session id so that we can later verify it
                current_session = self.state_manager.state.session_id

                # Initialize inventory manager with loaded data
                self.initialize_item_managers()

                # Make sure to load the saved inventory data into the inventory manager
                if hasattr(self.state_manager.state.player, 'inventory_data'):
                    inventory_data = self.state_manager.state.player.inventory_data
                    if inventory_data and hasattr(self, 'inventory_manager'):
                        self.logger.info("Loading saved inventory data into inventory manager")
                        self.inventory_manager.from_dict(inventory_data)

                        # Ensure GUI is updated with inventory data
                        if hasattr(self, "gui") and hasattr(self.gui, "initialize_inventory_widget"):
                            self.gui.initialize_inventory_widget()

                        # Ensure currency is synchronized
                        if hasattr(self.state_manager.state.player, 'inventory'):
                            player_inventory = self.state_manager.state.player.inventory
                            if "money" in player_inventory:
                                player_inventory["money"] = inventory_data["currency"].copy()
                                self.logger.info("Synchronized player.inventory.money with inventory_data.currency")

                # Launch the narrator API call
                summary_future = asyncio.run_coroutine_threadsafe(narrator_agent.process(context), loop)

                # Add loading indicator to UI if in GUI mode
                if hasattr(self, "gui"):
                    loadingWidget = MessageWidget("System", "#000000", self.gui)
                    loadingWidget.setMessage("Loading game summary...\n", gradual=False)
                    self.gui.conversationWidget.addMessage(loadingWidget)
                    # Schedule periodic checking and pass the captured session id
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(100, lambda: self._check_summary_future(summary_future, current_session))
                
                # If not in GUI mode, handle the summary directly
                else:
                    try:
                        # Wait with timeout
                        try:
                            summary_result = summary_future.result(timeout=10.0)
                            if summary_result.success:
                                welcome_message = summary_result.content
                                print(f"\n{welcome_message}\n")
                        except TimeoutError:
                            print("\nGame loaded successfully! (Summary generation timed out)")
                    except Exception as e:
                        print(f"\nGame loaded successfully! (Summary error: {e})")

            else:
                # Restore previous state if load failed
                self.state_manager.state = previous_state
                
                if hasattr(self, "gui"):
                    self.gui.output_text.append("Failed to load save.\n")
                else:
                    print("Failed to load save.")
        except Exception as e:
            self.logger.error(f"Error in _load_game_with_filename: {str(e)}", exc_info=True)

    def _check_summary_future(self, future, expected_session):
        if not self.state_manager.state or self.state_manager.state.session_id != expected_session:
            print("[DEBUG] Outdated summary response; current session does not match expected.")
            return
        if future.done():
            try:
                summary_result = future.result()
            except Exception as e:
                self.gui.displayTextSignal.emit("Failed to generate summary.\n", "Context")
                return
            if summary_result.success:
                welcome_message = summary_result.content
                
                # Clean the music tag from the welcome message
                welcome_message = re.sub(r'\{MUSIC:\s*[\w]+\s*\}', '', welcome_message, flags=re.IGNORECASE).strip()
                
                # Remove character stats section from the welcome message
                welcome_message = re.sub(r'Character\s+(Overview|Stats|Statistics)[\s\S]*?(Active Events|Quest Log|Location:|Inventory:)', r'\2', welcome_message, flags=re.IGNORECASE)
                
                # Extract mood from the original message (before stats removal)
                mood = self.llm_manager.extract_mood_from_response(summary_result.content)
                self.logger.debug(f"Extracted music mood from loaded game summary: {mood}")
                if mood:
                    self.llm_manager.update_music_mood(mood)
                    
                # Extract active events for quest log
                active_events_match = re.search(r'Active Events?:(.*?)(?:\n\n|\Z)', summary_result.content, re.IGNORECASE | re.DOTALL)
                active_events = []
                if active_events_match:
                    events_text = active_events_match.group(1).strip()
                    # Split by newlines or bullets
                    events = re.split(r'[\n•\-]+', events_text)
                    active_events = [event.strip() for event in events if event.strip()]
                    
                    # Update quest log with active events
                    if active_events and hasattr(self.gui, 'update_quest_log'):
                        quest_text = "Active Events:\n" + "\n".join(f"- {event}" for event in active_events)
                        self.gui.update_quest_log(quest_text)
                
                # Update stats tab
                if hasattr(self.gui, 'update_stats_tab'):
                    self.gui.update_stats_tab()

            else:
                welcome_message = "Game loaded successfully! (Failed to generate summary.)"
            if hasattr(self.gui, 'conversationWidget'):
                self.gui.conversationWidget.removeLastMessage()
            self.gui.displayTextSignal.emit(welcome_message + "\n", "Context")
        else:
            QTimer.singleShot(100, lambda: self._check_summary_future(future, expected_session))

    async def input_handler(self):
        loop = asyncio.get_running_loop()
        while self.is_running:
            try:
                # Run input() in a separate thread using the current event loop
                user_input = await loop.run_in_executor(None, input, "> ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input and self.game_loop:
                    self.game_loop.input_queue.put_nowait(user_input)

                    # Check if the command is a test command
                    if user_input.startswith("test_"):
                        result = self.command_processor.process_input(user_input)
                        if result.success:
                            print(result.message)
                        else:
                            print(f"Error: {result.message}")
                    else:
                        result = self.command_processor.process_input(user_input)

                        if result.success and isinstance(result.message, str) and (
                            result.message.startswith("System tests completed") or
                            result.message.startswith("Error running system tests")
                        ):
                            print(result.message)
                        elif not result.success or result.message == "Unknown command":
                            try:
                                if self.state_manager.state:
                                    context = AgentContext(
                                        current_location=self.state_manager.state.player.location,
                                        game_state=asdict(self.state_manager.state),
                                        conversation_history=self.state_manager.state.conversation_history,
                                        active_quests=self.state_manager.state.active_quests,
                                        context_manager=self.context_manager,
                                        context_type="general",
                                        context_evaluator=self.agents.get("context_evaluator")
                                    )
                                else:
                                    context = AgentContext(
                                        current_location="Unknown",
                                        game_state={},
                                        conversation_history=[],
                                        active_quests=[],
                                        context_manager=None,
                                        context_type="general",
                                        context_evaluator=None
                                    )

                                llm_result = await self.llm_manager.process_user_input(user_input, self.state_manager, context)

                                if llm_result.success:
                                    if llm_result.commands:
                                        for cmd, value in llm_result.commands.items():
                                            cmd_result = self.command_processor.process_input(f"{cmd} {value}")
                                            if not cmd_result.success:
                                                self.logger.warning(f"Failed to process LLM command: {cmd} {value}")

                                    narrative = llm_result.content.strip()
                                    if narrative:
                                        print("\n" + "=" * 80)
                                        print("Game Master:")
                                        print("-" * 80)
                                        print(narrative)
                                        print("=" * 80 + "\n")
                                else:
                                    print(f"\nError: {llm_result.error}\n")

                            except Exception as e:
                                self.logger.error(f"Error processing LLM response: {str(e)}")
                                print("\nSorry, I couldn't process that request. Please try again.")
                        else:
                            print(result.message)

                        if result.success and result.data and result.data.get("should_exit"):
                            print("\nSaving game before exit...")
                            try:
                                self.save_manager.create_save(self.state_manager, "exit_save", auto=True)
                                self.game_loop.is_running = False
                                self.is_running = False
                                print("Game saved. Goodbye!")
                                break
                            except Exception as e:
                                self.logger.error(f"Error during exit: {str(e)}")

            except Exception as e:
                self.logger.error(f"Error in input_handler: {str(e)}")
                self.is_running = False
                if self.game_loop:
                    self.game_loop.is_running = False

    async def run_llm_diagnostics(self):
        """Run comprehensive LLM system diagnostics"""
        print("\n=== Running LLM System Diagnostics ===\n")
        
        # 1. Check Configuration
        print("1. Configuration Check:")
        status = self.llm_manager.check_provider_status()
        print(f"- Initialized Providers: {status['initialized_providers']}")
        print(f"- Default Provider: {status['config']['default_provider']}")
        print(f"- Available in Config: {status['config']['available_providers']}")
        
        # 2. Agent Configuration
        print("\n2. Agent Configuration:")
        for agent, config in status['agents'].items():
            print(f"\n{agent}:")
            print(f"- Provider: {config['provider']}")
            print(f"- Provider Available: {config['provider_available']}")
            print(f"- Model: {config['model']}")
        
        # 3. Client Verification
        print("\n3. Client Verification:")
        for provider in status['config']['available_providers']:
            verification = await self.llm_manager.verify_client(provider)
            print(f"- {provider}: {'✓ Working' if verification else '❌ Failed'}")
        
        print("\n=== Diagnostic Complete ===\n")

    def handle_llm_debug(self, args: str) -> CommandResult:
        """Handle llm_debug command"""
        try:
            asyncio.create_task(self.run_llm_diagnostics())
            return CommandResult(True, "LLM diagnostics initiated")
        except Exception as e:
            return CommandResult(False, f"Error running diagnostics: {str(e)}")
        
    def _start_new_game_with_args(self, name: str, race: str, path: str, background: str, selected_scenario="default"):
        
        if hasattr(self, "music_manager"):
            current_info = self.music_manager.get_current_track_info()
            if current_info.get("mood", "ambient") != "ambient":
                self.music_manager.reset("ambient", use_crossfade=True)
            else:
                # If already ambient, simply ensure playback is active.
                self.music_manager.play()
        
        # Now clear previous messages when creating a new game
        if self.gui is not None:
            self.gui.conversationWidget.clearMessages()

        try:
            # Clear current game context to prevent memory leaks 
            self.clear_current_game_context()
            
            valid_backgrounds = self.state_manager.world_config_loader.get_backgrounds_for_path(path)
            if background not in valid_backgrounds:
                background = valid_backgrounds[0]
            success = self.state_manager.create_new_game(name, race, path, background)
            if not success:
                raise RuntimeError("Failed to create new game")
            
            self.initialize_item_managers()
            
            # Get scenario based on selection
            scenario = None
            if selected_scenario == "default":
                # Use the standard background-based scenario loading
                scenario = self.state_manager.world_config_loader.load_starting_scenario(background)
                
                # If not found, try to find any scenario for this path and background
                if not scenario:
                    self.logger.debug(f"No direct scenario found for background {background}, checking path-level scenarios")
                    path_scenarios = self.state_manager.world_config_loader.get_scenarios_for_path(path)
                    for scenario_key, scenario_data in path_scenarios.items():
                        applicable_backgrounds = scenario_data.get("applicable_backgrounds", [])
                        
                        # Check using different formats of the background name
                        bg_lower = background.lower()
                        bg_underscored = bg_lower.replace(" ", "_")
                        bg_variations = [bg_lower, bg_underscored]
                        
                        # Compare with all variations of background names in applicable_backgrounds
                        applicable_lower = [str(bg).lower() for bg in applicable_backgrounds]
                        if any(bg_var in applicable_lower for bg_var in bg_variations):
                            self.logger.debug(f"Found matching scenario {scenario_key} for background {background}")
                            scenario = scenario_data
                            break
            else:
                # A specific scenario was selected
                path_scenarios = self.state_manager.world_config_loader.get_scenarios_for_path(path)
                if selected_scenario in path_scenarios:
                    scenario = path_scenarios[selected_scenario]
                    self.logger.info(f"Using explicitly selected scenario: {selected_scenario}")
                else:
                    self.logger.warning(f"Selected scenario {selected_scenario} not found in path {path}")
            
            # Build a single welcome message string
            if scenario:
                self.logger.info(f"Starting new game with scenario: {scenario.get('name', 'Unnamed')}")
                welcome_text = (
                    "Welcome to your adventure!\n"
                )
                
                # IMPORTANT: Add scenario data to state manager
                if hasattr(self.state_manager.state, 'scenario'):
                    self.state_manager.state.scenario = scenario
                else:
                    # If there's no scenario field, at least store the narrative elements
                    if hasattr(self.state_manager.state, 'narrative_elements'):
                        self.state_manager.state.narrative_elements = scenario.get('narrative_elements', {})
                
                # Add starting equipment if present
                if "starting_equipment" in scenario and self.inventory_manager:
                    self.logger.info(f"Adding starting equipment from scenario: {scenario.get('starting_equipment', [])}")
                    for item_id in scenario.get('starting_equipment', []):
                        try:
                            self.inventory_manager.add_item(item_id)
                            self.logger.debug(f"Added item {item_id} to inventory")
                        except Exception as e:
                            self.logger.error(f"Failed to add item {item_id}: {e}")
            else:
                self.logger.warning(f"No starting scenario found for background: {background}")
                welcome_text = "No starting scenario found for background: " + background

            # Display the welcome text gradually in one message widget.
            if self.gui:
                welcomeWidget = MessageWidget("System", self.gui.output_color, self.gui)
                welcomeWidget.setMessage(welcome_text, gradual=True)
                self.gui.conversationWidget.addMessage(welcomeWidget)
            
            # Save the initial game state
            success, _ = self.save_manager.create_save(self.state_manager, "initial_save", auto=True)
            
            # Initiate detailed narrative for the new game (the asynchronous call remains unchanged)
            context = AgentContext(
                current_location=self.state_manager.state.player.location,
                game_state=asdict(self.state_manager.state),
                conversation_history=self.state_manager.state.conversation_history,
                active_quests=self.state_manager.state.active_quests,
                context_manager=self.context_manager,
                context_type="initial",
                context_evaluator=self.agents.get("context_evaluator")
            )
            
            # Use scenario information in the prompt if available
            if scenario:
                # Add narrative elements from scenario to prompt
                narrative_elements = scenario.get("narrative_elements", {})
                introduction = narrative_elements.get("introduction", [])
                goals = narrative_elements.get("immediate_goals", [])
                
                # Format intro text
                intro_text = ""
                if isinstance(introduction, list):
                    intro_text = " ".join(introduction)
                else:
                    intro_text = str(introduction)
                    
                # Format goals text
                goals_text = ""
                if isinstance(goals, list):
                    goals_text = "\n".join([f"- {goal}" for goal in goals])
                else:
                    goals_text = str(goals)
                    
                context.game_state["current_input"] = (
                    "Provide a detailed introduction of the character. Include who they are, their background, "
                    "what led them to their current location, a description of the surroundings, immediate objectives, "
                    "and possible trajectories. Use the following scenario elements in your response:\n\n"
                    f"Scenario: {scenario.get('name', 'Unknown')}\n"
                    f"Location: {scenario.get('location', 'Unknown')}, {scenario.get('district', '')}\n"
                    f"Introduction: {intro_text}\n\n"
                    f"Immediate Goals:\n{goals_text}\n\n"
                    "Make the narrative immersive and informative, consistent with the scenario details."
                )
            else:
                context.game_state["current_input"] = (
                    "Provide a detailed introduction of the character. Include who they are, their background, "
                    "what led them to their current location, a description of the surroundings, immediate objectives, "
                    "and possible trajectories. Make the narrative immersive and informative."
                )

            # Add quest information to context
            if hasattr(self, 'quest_manager'):
                quest_summary = self.quest_manager.get_active_quests_summary()
                context.game_state["quest_summary"] = quest_summary
            async def initiate_narrative():
                # First, ensure we have the starting quests properly loaded
                if self.state_manager.state.active_quests:
                    # Format quests for inclusion in the prompt
                    quest_summary = "Starting Objectives:\n"
                    for i, quest in enumerate(self.state_manager.state.active_quests):
                        quest_summary += f"{i+1}. {quest.get('description', '')}\n"
                else:
                    quest_summary = "No starting objectives."
                
                # Create the context with explicit quest information
                context = AgentContext(
                    current_location=self.state_manager.state.player.location,
                    game_state=asdict(self.state_manager.state),
                    conversation_history=self.state_manager.state.conversation_history,
                    active_quests=self.state_manager.state.active_quests,
                    context_manager=self.context_manager,
                    context_type="initial",
                    context_evaluator=self.agents.get("context_evaluator")
                )
                
                # Add explicit starting quests instruction, including scenario information if available
                if scenario:
                    # Get narrative elements from scenario
                    narrative_elements = scenario.get("narrative_elements", {})
                    introduction = narrative_elements.get("introduction", [])
                    goals = narrative_elements.get("immediate_goals", [])
                    
                    # Format intro text
                    intro_text = ""
                    if isinstance(introduction, list):
                        intro_text = " ".join(introduction)
                    else:
                        intro_text = str(introduction)
                        
                    # Format goals text
                    goals_text = ""
                    if isinstance(goals, list):
                        goals_text = "\n".join([f"- {goal}" for goal in goals])
                    else:
                        goals_text = str(goals)
                    
                    context.game_state["current_input"] = (
                        "Provide a detailed introduction of the character. Include who they are, their background, "
                        "what led them to their current location, a description of the surroundings, and the immediate objectives "
                        f"which are based on this scenario:\n\n"
                        f"Scenario: {scenario.get('name', 'Unknown')}\n"
                        f"Location: {scenario.get('location', 'Unknown')}, {scenario.get('district', '')}\n"
                        f"Introduction: {intro_text}\n\n"
                        f"Immediate Goals:\n{goals_text}\n\n"
                        "Make the narrative immersive and informative, ensuring it's compatible with the character attending an academic setting."
                    )
                else:
                    context.game_state["current_input"] = (
                        "Provide a detailed introduction of the character. Include who they are, their background, "
                        "what led them to their current location, a description of the surroundings, and the immediate objectives "
                        f"which are:\n{quest_summary}\n"
                        "Make the narrative immersive and informative, ensuring it's compatible with the character attending an academic setting."
                    )
                
                response = await self.agents["narrator"].process(context)
                if response.success:
                    if self.gui is not None:
                        self.gui.displayTextSignal.emit(response.content, "GameMaster")
                    # Update music mood if extracted (if needed, though for initial it should not change)
                    mood = self.llm_manager.extract_mood_from_response(response.content)
                    self.logger.debug(f"Extracted music mood from new game response: {mood}")
                    if mood and mood.lower() != "ambient":
                        self.llm_manager.update_music_mood("ambient")
                else:
                    self.logger.error("Narrator failed to generate response for new game.")
            
            asyncio.run_coroutine_threadsafe(initiate_narrative(), self.loop)
            
            sys.stdout.flush()
            if self.gui is not None:
                QMetaObject.invokeMethod(self.gui, "update_output_from_queue", Qt.QueuedConnection)
                QMetaObject.invokeMethod(self.gui, "update_stats_tab", Qt.QueuedConnection)
                if scenario and "narrative_elements" in scenario and "immediate_goals" in scenario["narrative_elements"]:
                    # Use goals from the scenario
                    quest_text = "Immediate Objectives:\n" + "\n".join(
                        f"{i}. {goal}" for i, goal in enumerate(scenario["narrative_elements"]["immediate_goals"], 1)
                    )
                    QMetaObject.invokeMethod(self.gui, "update_quest_log", Qt.QueuedConnection, Q_ARG(str, quest_text))
                elif hasattr(self.state_manager.state, 'active_quests') and self.state_manager.state.active_quests:
                    # Use active quests if available
                    quest_text = "Active Quests:\n" + "\n".join(
                        f"{i}. {quest.get('description', '')}" for i, quest in enumerate(self.state_manager.state.active_quests, 1)
                    )
                    QMetaObject.invokeMethod(self.gui, "update_quest_log", Qt.QueuedConnection, Q_ARG(str, quest_text))
        except Exception as e:
            self.logger.error(f"Error in _start_new_game_with_args: {str(e)}")
            raise

    def sync_inventory_state(self):
        """Synchronize inventory state with player state"""
        if not self.state_manager or not self.state_manager.state:
            self.logger.warning("Cannot sync inventory: No active game state")
            return False
                
        player = self.state_manager.state.player
        
        # Ensure inventory manager exists
        if not hasattr(self, 'inventory_manager') or not self.inventory_manager:
            self.logger.warning("Cannot sync inventory: No inventory manager")
            return False
        
        # Sync inventory manager state to player state
        result = self.inventory_manager.sync_to_player_state(player)
        
        # Add better logging
        if result:
            equipped_count = sum(1 for item in self.inventory_manager.equipped_items.values() if item)
            backpack_count = len(self.inventory_manager.backpack)
            self.logger.info(f"Synced inventory to player state: {equipped_count} equipped items, {backpack_count} in backpack")
        else:
            self.logger.warning("Failed to sync inventory to player state")
            
        return result

async def main():
    """Main entry point"""
    try:
        # Initialize basic logging
        LoggingConfig.setup_logging()
        logger = LoggingConfig.get_logger("Main")
        logger.info("Game starting up...")
        
        game_manager = GameManager()
        await game_manager.start_game()
    except KeyboardInterrupt:
        print("\nGame terminated by user.")
        logger.info("Game terminated by user")
    except Exception as e:
        print(f"\nCritical error: {str(e)}")
        logger.error(f"Critical error in main: {str(e)}", exc_info=True)
    finally:
        print("\nThank you for playing!")
        logger.info("Game shut down")

if __name__ == "__main__":
    asyncio.run(main())