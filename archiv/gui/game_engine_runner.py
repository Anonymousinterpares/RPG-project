#path/gui/game_engine_runner.py

import sys
import os
import asyncio
import threading
from queue import Empty
from PySide6.QtCore import QMetaObject, Qt
from main import GameManager  # Ensure this import is correct in your project
from gui.widgets import QueueStream  # Used for stdout redirection
from gui.message_widget import MessageWidget
from core.utils.logging_config import LoggingConfig, LogCategory

def start_game_engine(gui):
    """
    Creates and starts the game engine in a background thread.
    This function sets up a new asyncio event loop, creates a GameManager,
    and then continuously processes commands from the GUI's input queue.
    """
    # Create a new event loop for the game engine.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Instantiate GameManager and assign it to both the GUI and game manager.
    gm = GameManager()
    gm.gui = gui
    gm.loop = loop
    gui.gm = gm
    gm.command_processor.gui = gui
    logger = LoggingConfig.get_logger(__name__, LogCategory.GAME)

    # Redirect stdout to the GUI's output queue.
    sys.stdout = QueueStream(gui.output_queue, gui)
    
    logger.debug("start_game_engine: Starting game engine in background thread...")

    async def gui_process_input():
        while True:
            # Check if GUI still exists
            if not hasattr(gui, 'conversationWidget') or not gui.conversationWidget:
                logger.debug(" GUI no longer available, terminating input processing")
                break
            if not gui.input_queue.empty():
                cmd = gui.input_queue.get_nowait()
                # print(f"[DEBUG] gui_process_input: Processing command: {cmd}")
                if cmd.startswith("new_game|"):
                    parts = cmd.split("|", 4)
                    if len(parts) == 5:
                        gm._start_new_game_with_args(parts[1], parts[2], parts[3], parts[4])
                    else:
                        logger.debug(" gui_process_input: Invalid new_game command format.")
                elif cmd.startswith("load_game|"):
                    parts = cmd.split("|")
                    if len(parts) == 2:
                        gm._load_game_with_filename(parts[1])
                    else:
                        logger.debug("gui_process_input: Invalid load_game command format.")
                elif cmd == "save":
                    gm.save_manager.create_save(gm.state_manager, "manual_save", auto=False)
                    logger.debug("gui_process_input: Save game command processed.")
                else:
                    if cmd.lower() in gm.command_processor.commands:
                        # Process the recognized command and do not forward to agent chain.
                        result = gm.command_processor.process_input(cmd)
                        # (Optional: log the result)
                        logger.debug(f"Recognized command '{cmd}' processed.")
                    else:
                        # Not recognized – forward to agent chain.
                        from dataclasses import asdict
                        from core.agents.base_agent import AgentContext
                        context = AgentContext(
                            current_location=gm.state_manager.state.player.location if gm.state_manager.state else "Unknown",
                            game_state=asdict(gm.state_manager.state) if gm.state_manager.state else {},
                            conversation_history=gm.state_manager.state.conversation_history if gm.state_manager.state else [],
                            active_quests=gm.state_manager.state.active_quests if gm.state_manager.state else [],
                            context_manager=gm.context_manager,
                            context_type="general",
                            context_evaluator=gm.agents.get("context_evaluator")
                        )
                        try:
                            gm.pending_api_task = asyncio.create_task(
                                gm.llm_manager.process_user_input(cmd, gm.state_manager, context)
                            )
                            llm_result = await asyncio.wait_for(gm.pending_api_task, timeout=40.0)
                        except asyncio.TimeoutError:
                            logger.debug("gui_process_input: LLM request timed out")
                            llm_result = None
                        finally:
                            gm.pending_api_task = None
                        if llm_result and llm_result.success:
                            # Use the displayTextSignal of GameGUI to update the GUI from the main thread.
                            gui.displayTextSignal.emit(llm_result.content, "GameMaster")
                        else:
                            logger.debug("LLM error:", llm_result.error if llm_result else "No result")

                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(gui, "update_stats_tab", Qt.QueuedConnection)
            await asyncio.sleep(0.1)

    # Schedule the gui_process_input coroutine on the event loop.
    loop.create_task(gui_process_input())
    
    # Start the event loop (this call blocks indefinitely).
    loop.run_forever()
    
    return gm

