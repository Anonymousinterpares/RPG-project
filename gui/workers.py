from PySide6.QtCore import QObject, Signal

from core.utils.logging_config import get_logger
logger = get_logger("WORKERS") 

class SaveGameWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, game_engine, slot, quicksave=False):
        super().__init__()
        self.game_engine = game_engine
        self.slot = slot
        self.quicksave = quicksave

    def run(self):
        try:
            # The GameEngine's save_game method expects 'auto_save', not 'quick_save'.
            # For a manual save initiated via the dialog, we pass neither, letting the
            # engine default to a standard, non-auto-save.
            screenshot = self.game_engine.save_game(self.slot)
            self.finished.emit(screenshot)
        except Exception as e:
            self.error.emit(str(e))

class LoadGameWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, game_engine, slot):
        super().__init__()
        self.game_engine = game_engine
        self.slot = slot

    def run(self):
        try:
            self.game_engine.load_game(self.slot)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class NewGameWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    
    def __init__(self, game_engine, character_data):
        super().__init__()
        self.game_engine = game_engine
        self.character_data = character_data

    def run(self):
        """Execute the long-running new game creation process."""
        try:
            # The GameEngine's method is start_new_game and it expects keyword arguments,
            # not a single dictionary.
            logger.info(f"NewGameWorker: Starting new game with data: {self.character_data}")
            
            # Unpack the dictionary into keyword arguments for the start_new_game method.
            # Ensure all required keys are present with sensible defaults if necessary.
            initial_narration_state = self.game_engine.start_new_game(
                player_name=self.character_data.get('name', 'Player'),
                race=self.character_data.get('race', 'Human'),
                path=self.character_data.get('path', 'Wanderer'),
                origin_id=self.character_data.get('origin_id'),
                sex=self.character_data.get('sex', 'Male'),
                background=self.character_data.get('description'), # The 'description' from origin is the background
                character_image=self.character_data.get('character_image'),
                stats=self.character_data.get('stats')
            )

            # The lifecycle method now returns the entire game state. We need the intro narration from it.
            initial_narration = ""
            if initial_narration_state and hasattr(initial_narration_state, 'initial_narration'):
                initial_narration = initial_narration_state.initial_narration
            
            if not initial_narration:
                logger.warning("New game started but returned no initial narration.")

            self.finished.emit(initial_narration or "Your adventure begins...")
        except Exception as e:
            logger.error(f"Error starting new game in worker thread: {e}", exc_info=True)
            self.error.emit(str(e))
