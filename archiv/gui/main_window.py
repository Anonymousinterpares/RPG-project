# gui/main_window.py.py
import datetime
import os
import sys
import json
import logging
import asyncio
import threading
import queue
from queue import Empty, Queue
import traceback

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QFrame, QLabel, QScrollArea, QTextEdit,
                               QTabBar, QTabWidget, QGraphicsView, QGraphicsPixmapItem,
                               QGraphicsProxyWidget, QGraphicsScene, QSizePolicy, QStackedWidget)
from PySide6.QtGui import QPixmap, QFont, QTextCursor, QPainter, QLinearGradient, QColor, QPen
from PySide6.QtCore import Qt, QEvent, QSize, Slot, Signal, QTimer
from dataclasses import asdict
from gui.widgets import CustomButton, QueueStream
from core.utils.logging_config import LoggingConfig
from gui.game_engine_runner import start_game_engine
from gui.logging_handlers import QtLogHandler, BackgroundThreadHandler
from gui.conversation_widget import ConversationWidget
from gui.message_widget import MessageWidget
from gui.advanced_config_editor.custom_widgets import AutoResizingPlainTextEdit
from gui.message_widget import MessageWidget
from gui.tab_widgets import OverlayTabWidget
from sound.music_manager import MusicManager
from gui.widgets.music_controls import MusicControls
from core.utils.logging_config import LoggingConfig, LogCategory
from gui.quest_widgets import QuestListWidget
from core.inventory.item_manager import InventoryManager
from core.inventory.item import EquipmentSlot
from gui.inventory.inventory_widget import InventoryWidget

ENABLE_DEV_SETTINGS = True      # Set to False in production to hide Developer Settings button
REQUIRE_DEV_CREDENTIALS = False # Set to True in production to require credentials for enabling debug mode / developer settings

class OutputScrollArea(QWidget):
    def __init__(self, bg_image_path, parent=None):
        super().__init__(parent)
        self.bg_pixmap = QPixmap(bg_image_path)
        self.setStyleSheet("background: transparent;")
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.bg_pixmap.isNull():
            rect = self.rect()
            scaled_pixmap = self.bg_pixmap.scaled(
                rect.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            painter.drawPixmap(rect, scaled_pixmap)
        super().paintEvent(event)

class SafeZoneContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.margin = 105
        
        # Create layout for this container
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(self.margin, self.margin, self.margin, self.margin)
        self.layout.setSpacing(0)
        
        # Create scroll area for content
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 12px;
                margin: 0px;
            }
        """)
        
        # Add scroll area to layout
        self.layout.addWidget(self.scroll_area)

class ClickableTabBar(QTabBar):
    clicked = Signal(int)  # Custom signal emitting the clicked tab index

    def mousePressEvent(self, event):
        tab_index = self.tabAt(event.pos())
        if tab_index >= 0:
            self.clicked.emit(tab_index)
        super().mousePressEvent(event)

# --- Custom Container Widget with Background ---
class ScaledContainerWidget(QWidget):
    def __init__(self, bg_pixmap: QPixmap = None, parent=None):
        super().__init__(parent)
        self.designSize = QSize(800, 600)
        self.setMinimumSize(self.designSize)  # Use minimum size so that it can expand.
        self.bg_pixmap = bg_pixmap
        # Make widget transparent so the scene background is visible behind it.
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Optionally, you could fill with a semi-transparent color if desired.
        # For example:
        # painter.fillRect(self.rect(), QColor(255, 255, 255, 180))
        super().paintEvent(event)

# --- Main GUI using QGraphicsView for Proportional Scaling ---
class GameGUI(QMainWindow):
    displayTextSignal = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.output_color = "#000000"  # Black color for text
        self.displayTextSignal.connect(self.display_text_from_signal)
        self.logger = LoggingConfig.get_logger(__name__, LogCategory.LLM)
        self.logger.propagate = True  # Ensure messages propagate to the root logger.
        print("GameGUI logger propagate:", self.logger.propagate)
        print("GameGUI effective level:", self.logger.getEffectiveLevel())

        self.setWindowTitle("RPG Game")
        # Load resolution from game settings (default to 800x600)
        try:
            import json
            with open("config/game_settings.json", "r") as f:
                settings = json.load(f)
            res_text = settings.get("gui_resolution", "800x600")
        except Exception as e:
            res_text = "800x600"
        width, height = map(int, res_text.split("x"))
        self.setFixedSize(width, height)  # Changed from resize() to setFixedSize() to disable manual resizing

        # Compute container size using uniform 20px margin on all sides.
        container_width = width - 40
        container_height = height - 40

        # Load the background image.
        try:
            self.bg_pixmap = QPixmap("images/background.png")
        except Exception as e:
            print(f"[DEBUG] Could not load background image: {e}")
            self.bg_pixmap = QPixmap()

        # Create our container widget and set its minimum size to fill available space.
        self.ui_container = ScaledContainerWidget(self.bg_pixmap)
        self.ui_container.setMinimumSize(QSize(container_width, container_height))  # Changed from setFixedSize to setMinimumSize
        self.create_widgets(self.ui_container)
        self.load_default_theme()

        # Create handlers
        self.qt_handler = QtLogHandler(self.tab_debug)
        self.qt_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.qt_handler.setFormatter(formatter)

        # Create background thread handler
        self.background_handler = BackgroundThreadHandler()
        # Connect its signal to our processing method using queued connection
        self.background_handler.logReceived.connect(self.process_background_log, 
                                                Qt.QueuedConnection)

        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Add main thread handler
        root_logger.addHandler(self.qt_handler)

        # Set up the QGraphicsScene.
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, width, height)
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            self.background_item = QGraphicsPixmapItem(self.bg_pixmap)
            self.background_item.setZValue(0)
            offset_x = -(self.bg_pixmap.width() - width) / 2
            offset_y = -(self.bg_pixmap.height() - height) / 2
            self.background_item.setPos(offset_x, offset_y)
            self.scene.addItem(self.background_item)
        else:
            self.background_item = None

        self.proxy = QGraphicsProxyWidget()
        self.proxy.setWidget(self.ui_container)
        self.proxy.setZValue(1)
        self.scene.addItem(self.proxy)

        # Position the container at (20,20) with no scaling.
        self.proxy.setPos(20, 20)

        self.view = QGraphicsView()
        self.view.setScene(self.scene)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.view.setFrameStyle(0)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(self.view)

        # Setup queues
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.logger.debug(f"GameGUI.__init__: input_queue id: {id(self.input_queue)}")

        # Start game engine in a separate background thread
        self.game_thread = threading.Thread(target=lambda: start_game_engine(self), daemon=True)
        self.game_thread.start()

        QTimer.singleShot(1000, self.assign_gui_to_llm_manager)

        self.setup_logging_system()

    def apply_music_settings_from_config(self):
        """Apply music settings from game configuration to the music manager"""
        if not hasattr(self, 'gm') or not self.gm:
            self.logger.warning("Game manager not available for music settings")
            return
        
        try:
            # Get music settings from game config
            music_settings = self.gm.config.settings.get("music", {})
            if not music_settings:
                self.logger.warning("No music settings found in game config")
                return
                
            # Apply settings to music manager
            volume = music_settings.get("volume", 40)
            crossfade = music_settings.get("crossfade_duration", 3.0)
            default_mood = music_settings.get("default_mood", "ambient")
            
            self.logger.info(f"Applying music settings from config: volume={volume}, "
                            f"crossfade={crossfade}, mood={default_mood}")
            
            # Update music controls to match config
            self.music_controls.set_volume(volume)
            
            # Update music manager with new settings
            self.music_manager.update_settings(
                volume=volume,
                crossfade_duration=crossfade,
                default_mood=default_mood
            )
        except Exception as e:
            self.logger.error(f"Error applying music settings: {str(e)}")

    def display_text_from_signal(self, text: str, sender: str):
        # For GameMaster/Context outputs, use default output color; for user, use input color.
        color = "black"
        widget = MessageWidget(sender, color, self)
        widget.setMessage(text, gradual=True)
        self.conversationWidget.addMessage(widget)

    def setup_logging_system(self):
        """Set up comprehensive logging system"""
        # Create our handlers
        self.qt_handler = QtLogHandler(self.tab_debug)
        self.background_handler = BackgroundThreadHandler()
        
        # Set levels and formatters
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.qt_handler.setLevel(logging.DEBUG)
        self.qt_handler.setFormatter(formatter)
        self.background_handler.setLevel(logging.DEBUG)
        self.background_handler.setFormatter(formatter)
        
        # Connect background handler signal
        self.background_handler.logReceived.connect(
            self.process_background_log, 
            Qt.QueuedConnection
        )
        
        # Get root logger and configure it
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Remove any existing handlers of our types
        for handler in root_logger.handlers[:]:
            if isinstance(handler, (QtLogHandler, BackgroundThreadHandler)):
                root_logger.removeHandler(handler)
        
        # Add our handlers
        root_logger.addHandler(self.qt_handler)
        
        # Ensure all loggers propagate
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            logger.propagate = True
            
        self.logger.info("QtLogHandler is now attached to the root logger.")

    @Slot(object)
    def process_background_log(self, record):
        """Process log records from background thread in the main thread"""
        try:
            if not record:
                self.logger.info("Received empty record in process_background_log", file=sys.stderr)
                return

            # Format the record using the same style as QtLogHandler
            if record.levelno == logging.DEBUG:
                color = "gray"
            elif record.levelno == logging.INFO:
                color = "black"
            elif record.levelno == logging.WARNING:
                color = "orange"
            elif record.levelno == logging.ERROR:
                color = "red"
            elif record.levelno == logging.CRITICAL:
                color = "red; font-weight:bold; text-decoration: underline;"
            else:
                color = "black"
            
            try:
                msg = self.background_handler.format(record)
            except Exception as format_error:
                self.logger.error(f"Error formatting record: {format_error}", file=sys.stderr)
                msg = str(record.msg)  # Fallback to raw message

            html_msg = f'<span style="color:{color};">{msg}</span>'
            
            self.tab_debug.setReadOnly(False)
            self.tab_debug.append(html_msg)
            self.tab_debug.moveCursor(QTextCursor.End)
            self.tab_debug.setReadOnly(True)
        except Exception as e:
            self.logger.error(f"Error in process_background_log: {e}", file=sys.stderr)
            traceback.print_exc()

    def show_quest_details(self, quest_id):
        """Show details for the quest with the given ID"""
        if hasattr(self, 'gm') and self.gm and hasattr(self.gm, 'quest_manager'):
            quest = self.gm.quest_manager.get_quest_by_id(quest_id)
            if quest:
                from gui.quest_widgets import QuestDetailDialog
                dialog = QuestDetailDialog(quest, self)
                dialog.exec_()

    @Slot(str)
    def update_quest_log(self, quest_text=None):
        """Update the quest log display with current quest data"""
        if not hasattr(self, 'gm') or not self.gm or not hasattr(self.gm, 'quest_manager'):
            if quest_text:
                # Fall back to the old behavior if quest_manager is not available
                self.tab_quests.setPlainText(quest_text)
            return
            
        # Use the new quest manager-based display
        active_quests = self.gm.quest_manager.get_active_quests()
        completed_quests = self.gm.quest_manager.get_completed_quests()
        self.tab_quests.update_quests(active_quests, completed_quests)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        outer_width = self.view.width()
        outer_height = self.view.height()
        self.scene.setSceneRect(0, 0, outer_width, outer_height)
        if self.background_item and self.bg_pixmap and not self.bg_pixmap.isNull():
            offset_x = -(self.bg_pixmap.width() - outer_width) / 2
            offset_y = -(self.bg_pixmap.height() - outer_height) / 2
            self.background_item.setPos(offset_x, offset_y)
        container_width = outer_width - 40
        container_height = outer_height - 40
        self.ui_container.setMinimumSize(QSize(container_width, container_height))  # Changed from setFixedSize to setMinimumSize
        self.proxy.setGeometry(20, 20, container_width, container_height)

    def create_widgets(self, parent):
        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        ## --- Header Section ---
        header_frame = QFrame(parent)
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 0, 10, 0)
        header_layout.setSpacing(5)

        # Create music controls in header
        self.music_controls = MusicControls(header_frame)
        self.music_controls.set_playing_state(False)  # Default is not playing
        try:
            # Get default music settings (will be properly updated later)
            default_music_settings = {
                "volume": 40, 
                "crossfade_duration": 3.0, 
                "default_mood": "ambient"
            }
            
            # Load from game_settings.json if possible
            try:
                import json
                with open("config/game_settings.json", "r") as f:
                    settings = json.load(f)
                    if "music" in settings:
                        default_music_settings = settings["music"]
                        self.logger.info("Loaded music settings from game_settings.json")
            except Exception as e:
                self.logger.warning(f"Could not load music settings from file: {e}")
            
            self.logger.info(f"Initializing MusicManager with settings: {default_music_settings}")
        except Exception as e:
            self.logger.warning(f"Error getting music settings: {e}")
            default_music_settings = {"volume": 40, "crossfade_duration": 3.0, "default_mood": "ambient"}

        self.music_manager = MusicManager(
            initial_volume=default_music_settings.get("volume", 40),
            crossfade_duration=default_music_settings.get("crossfade_duration", 3.0),
            default_mood=default_music_settings.get("default_mood", "ambient")
        )
        self.music_manager.gui = self 
        self.music_manager.stateChanged.connect(self.music_controls.set_playing_state)
        
        # Connect music control signals
        self.music_controls.playPauseClicked.connect(self.on_music_play_pause)
        self.music_controls.nextClicked.connect(self.on_music_next)
        self.music_controls.previousClicked.connect(self.on_music_previous)
        self.music_controls.muteClicked.connect(self.on_music_mute)
        self.music_controls.volumeChanged.connect(self.on_music_volume)
        try:
            import json
            with open("config/gui_themes.json", "r") as f:
                themes_data = json.load(f)
            theme = themes_data["themes"].get("Classic", {})
            logo_path = theme.get("logo_image", "images/header_title.png")
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                self.logo_label = QLabel(header_frame)
                self.logo_label.setPixmap(pixmap.scaledToHeight(60, Qt.SmoothTransformation))
                self.logo_label.setStyleSheet("background: transparent;")
                # Center: Logo
                header_layout.addStretch()
                header_layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)
                header_layout.addStretch()
                # Right side: Music controls
                header_layout.addWidget(self.music_controls, alignment=Qt.AlignRight)
            else:
                raise Exception("Logo image not found")
        except Exception as e:
            self.logo_label = QLabel("Logo", header_frame)
            header_layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)
        main_layout.addWidget(header_frame)

        ## --- Main Content (Middle Area) ---
        middle_frame = QFrame(parent)
        middle_frame.setStyleSheet("background: transparent;")
        middle_layout = QHBoxLayout(middle_frame)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        main_layout.addWidget(middle_frame, stretch=1)

        # Left Panel (Game Menu)
        left_panel = QFrame(middle_frame)
        left_panel.setFixedWidth(150)
        left_panel.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)

        self.left_buttons = []
        try:
            with open("config/gui_themes.json", "r") as f:
                themes_data = json.load(f)
            theme = themes_data["themes"].get("Classic", {})
            
            # Create and theme each button
            btn_new = CustomButton("New Game", left_panel)
            btn_new.clicked.connect(self.on_new_game)
            btn_new.update_theme(theme)
            self.left_buttons.append(btn_new)
            
            btn_load = CustomButton("Load", left_panel)
            btn_load.clicked.connect(self.on_load_game)
            btn_load.update_theme(theme)
            self.left_buttons.append(btn_load)
            
            btn_save = CustomButton("Save Game", left_panel)
            btn_save.clicked.connect(self.on_save_game)
            btn_save.update_theme(theme)
            self.left_buttons.append(btn_save)
            
            btn_settings = CustomButton("Settings", left_panel)
            btn_settings.clicked.connect(self.on_settings)
            btn_settings.update_theme(theme)
            self.left_buttons.append(btn_settings)
            
            btn_quit = CustomButton("Quit", left_panel)
            btn_quit.clicked.connect(self.on_quit)
            btn_quit.update_theme(theme)
            self.left_buttons.append(btn_quit)
            
            for btn in self.left_buttons:
                left_layout.addWidget(btn)
        except Exception as e:
            self.logger.debug(f"Error loading button theme: {e}")
            # Create buttons without theme if theme loading fails
            buttons_data = [
                ("New Game", self.on_new_game),
                ("Load", self.on_load_game),
                ("Save Game", self.on_save_game),
                ("Settings", self.on_settings),
                ("Quit", self.on_quit)
            ]
            for text, handler in buttons_data:
                btn = CustomButton(text, left_panel)
                btn.clicked.connect(handler)
                self.left_buttons.append(btn)
                left_layout.addWidget(btn)

        left_layout.addStretch()
        for btn in self.left_buttons:
            btn.update_theme(theme)

        middle_layout.addWidget(left_panel)

        # --- Wrap the conversationWidget in a QScrollArea with a fixed background image and vertical padding
        self.conversationWidget = ConversationWidget(self)
        self.conversationWidget.setStyleSheet("background: transparent;")

        # Create a safe frame that will clip its child to a rectangle inset by 105 pixels.

        self.safeFrame = QFrame()
        self.safeFrame.setStyleSheet("background: transparent;")  # Transparent so background shows.
        safeFrameLayout = QVBoxLayout(self.safeFrame)
        safeFrameLayout.setContentsMargins(0, 0, 0, 0)
        safeFrameLayout.setSpacing(0)
        safeFrameLayout.addWidget(self.conversationWidget)
        self.safeFrame.setLayout(safeFrameLayout)

        # Create the OutputScrollArea as before
        import os
        bg_path = os.path.abspath("images/output_bckg.png").replace("\\", "/")
        self.outputArea = OutputScrollArea(bg_path, middle_frame)

        # Create safe zone container
        self.safeZone = SafeZoneContainer(self.outputArea)
        self.outputArea.layout.addWidget(self.safeZone)

        # Create conversation widget
        self.conversationWidget = ConversationWidget()
        self.safeZone.scroll_area.setWidget(self.conversationWidget)

        # Add output area to middle layout
        middle_layout.addWidget(self.outputArea, stretch=1)

        # Optional: Add fade effects at safe zone boundaries
        fade_size = 40  # Adjust this value to control fade intensity
        fade_style = f"""
            SafeZoneContainer {{
                
                background: transparent;
            }}
            SafeZoneContainer > QScrollArea {{
                background: transparent;
                border: none;
            }}
            SafeZoneContainer > QScrollArea > QWidget {{
                background: transparent;
            }}
            SafeZoneContainer > QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
        """
        self.safeZone.setStyleSheet(fade_style)




        # --- Right Panel (Tabs) – New Collapsible Design ---
        
        # First, create the container frame for the right panel
        self.right_panel_container = QFrame(middle_frame)
        self.right_panel_container.setStyleSheet("background: transparent;")
        right_panel_layout = QVBoxLayout(self.right_panel_container)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(0)

        # Now create the OverlayTabWidget with correct parent
        self.info_tabs = OverlayTabWidget(self.right_panel_container)
        self.info_tabs.setStyleSheet("background: transparent;")
        self.info_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Helper function to create tab content
        def createTabContent():
            widget = QTextEdit()
            widget.setReadOnly(True)
            widget.setStyleSheet("background-color: #d9caaa;")
            return widget

        # Add tabs with content widgets
        self.tab_stats = createTabContent()
        self.tab_stats.setFont(QFont("Garamond", 10))
        self.tab_stats.setStyleSheet("background-color: #d9caaa;")
        self.info_tabs.addTab(self.tab_stats, "Stats")

        self.tab_quests = QuestListWidget(self)
        self.tab_quests.questClicked.connect(self.show_quest_details)
        self.tab_quests.setStyleSheet("background-color: #d9caaa;")
        self.info_tabs.addTab(self.tab_quests, "Quest Log")

        self.tab_inventory = QWidget()
        self.tab_inventory_layout = QVBoxLayout(self.tab_inventory)
        self.tab_inventory_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_quests.setStyleSheet("background-color: #d9caaa;")
        self.info_tabs.addTab(self.tab_inventory, "Inventory")

        self.tab_debug = createTabContent()
        self.tab_debug.setFont(QFont("Courier", 9))
        self.tab_debug.setStyleSheet("background-color: #d9caaa; color: black;")
        self.info_tabs.addTab(self.tab_debug, "Debug")

        # Add the tabs to the right panel
        right_panel_layout.addWidget(self.info_tabs)

        # Set the initial width
        collapsed_width = self.info_tabs.tabBar().sizeHint().width() + 10
        self.right_panel_container.setFixedWidth(collapsed_width)  # Change from setMinimumWidth to setFixedWidth

        # Add the right panel container to the middle layout
        middle_layout.addWidget(self.right_panel_container, stretch=0)

        ## --- Bottom Section (Command Input) ---
        bottom_frame = QFrame(parent)
        bottom_frame.setFixedHeight(40)
        bottom_frame.setStyleSheet("background: transparent;")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(5, 5, 5, 5)
        bottom_layout.setSpacing(5)
        
        self.command_entry = AutoResizingPlainTextEdit(bottom_frame, min_lines=1, max_lines=5)
        self.command_entry.setFont(QFont("Garamond", 12))
        self.command_entry.setStyleSheet("background: rgba(255, 255, 255, 220); color: black; border: 1px solid #ccc; border-radius: 4px;")
        self.command_entry.installEventFilter(self)
        bottom_layout.addWidget(self.command_entry, stretch=1)
        self.control_buttons = []
        send_button = CustomButton("Send", bottom_frame)
        send_button.clicked.connect(self.on_command_send)
        self.control_buttons.append(send_button)
        bottom_layout.addWidget(send_button)
        send_button.update_theme(theme)
        main_layout.addWidget(bottom_frame)

    def initialize_inventory_widget(self):
        """Initialize the inventory widget when game state is available"""
        try:
            if hasattr(self, 'gm') and self.gm and self.gm.state_manager.state:
                # First, check if inventory manager exists, create if not
                if not hasattr(self.gm, 'inventory_manager'):
                    self.gm.inventory_manager = InventoryManager(self.gm.config)
                    self.logger.info("Created new inventory manager")
                    
                    # If player has inventory data, load it
                    if hasattr(self.gm.state_manager.state.player, 'inventory_data') and self.gm.state_manager.state.player.inventory_data:
                        inventory_data = self.gm.state_manager.state.player.inventory_data
                        self.logger.info(f"Loading inventory data with {len(inventory_data.get('backpack', []))} backpack items and " + 
                                        f"{len(inventory_data.get('equipped_items', {}))} equipped items")
                        self.gm.inventory_manager.from_dict(inventory_data)
                    else:
                        # Check if this is a new game (no conversation history)
                        is_new_game = len(self.gm.state_manager.state.conversation_history) == 0
                        if is_new_game:
                            self.logger.info("New game with no inventory data - adding default items")
                            self.gm.inventory_manager.add_item("item_copper_sword")
                            self.gm.inventory_manager.add_item("item_leather_boots")
                            self.gm.inventory_manager.add_item("item_health_potion", 3)  # 3 health potions
                            
                            # Save changes back to player's inventory_data
                            self.gm.state_manager.state.player.inventory_data = self.gm.inventory_manager.to_dict()
                else:
                    # If inventory manager exists but was not loaded from saved state
                    if not self.gm.inventory_manager.backpack and not any(self.gm.inventory_manager.equipped_items.values()):
                        if hasattr(self.gm.state_manager.state.player, 'inventory_data') and self.gm.state_manager.state.player.inventory_data:
                            self.logger.info("Reloading inventory data into existing inventory manager")
                            self.gm.inventory_manager.from_dict(self.gm.state_manager.state.player.inventory_data)
                
                # Create inventory widget if needed
                if not hasattr(self, 'inventory_widget') or not self.inventory_widget:
                    # Clear inventory tab content first
                    for i in reversed(range(self.tab_inventory_layout.count())):
                        widget = self.tab_inventory_layout.itemAt(i).widget()
                        if widget:
                            widget.setParent(None)
                    
                    # Create and add inventory widget
                    self.inventory_widget = InventoryWidget(self.gm.inventory_manager, self)
                    self.tab_inventory_layout.addWidget(self.inventory_widget)
                    
                    # Connect signals to handle inventory actions
                    self.inventory_widget.itemEquipped.connect(self.on_item_equipped)
                    self.inventory_widget.itemUnequipped.connect(self.on_item_unequipped)
                    self.inventory_widget.itemExamined.connect(self.on_item_examined)
                    self.inventory_widget.itemRemoved.connect(self.on_item_removed)
                    
                    self.logger.info("Created and connected inventory widget")
                else:
                    # Update existing widget
                    self.inventory_widget.inventory_manager = self.gm.inventory_manager
                    self.inventory_widget.update_equipment_display()
                    self.inventory_widget.update_backpack_display()
                    self.logger.info("Updated existing inventory widget")
        except Exception as e:
            self.logger.error(f"Error initializing inventory widget: {e}", exc_info=True)

    @Slot(str)
    def on_item_removed(self, item_id):
        """Handle when an item is removed from inventory"""
        if not hasattr(self, 'gm') or not self.gm:
            return
            
        # Save inventory state to player
        if hasattr(self.gm.state_manager.state.player, 'inventory_data'):
            self.gm.state_manager.state.player.inventory_data = self.gm.inventory_manager.to_dict()

    @Slot(str)
    def on_item_equipped(self, item_id):
        """Handle when an item is equipped"""
        if not hasattr(self, 'gm') or not self.gm:
            return
                
        # Update stats if needed due to item bonuses
        if hasattr(self, 'update_stats_tab'):
            self.update_stats_tab()
                
        # Save inventory state to player using sync method
        if hasattr(self.gm, 'sync_inventory_state'):
            self.gm.sync_inventory_state()
            self.logger.info(f"Synchronized inventory state after equipping item {item_id}")
        else:
            # Explicit sync if sync_inventory_state method not available
            if hasattr(self.gm, 'inventory_manager') and hasattr(self.gm.state_manager, 'state'):
                self.gm.inventory_manager.sync_to_player_state(self.gm.state_manager.state.player)
                self.logger.info(f"Direct sync of inventory after equipping item {item_id}")
        
    @Slot(object)  # Use generic object type to handle both string and enum
    def on_item_unequipped(self, slot):
        """Handle when an item is unequipped"""
        if not hasattr(self, 'gm') or not self.gm:
            return
                
        # Update stats if needed due to item bonuses
        if hasattr(self, 'update_stats_tab'):
            self.update_stats_tab()
                
        # Save inventory state to player using sync method
        if hasattr(self.gm, 'sync_inventory_state'):
            self.gm.sync_inventory_state()
            self.logger.info(f"Synchronized inventory state after unequipping from slot {slot}")
        else:
            # Explicit sync if sync_inventory_state method not available
            if hasattr(self.gm, 'inventory_manager') and hasattr(self.gm.state_manager, 'state'):
                self.gm.inventory_manager.sync_to_player_state(self.gm.state_manager.state.player)
                self.logger.info(f"Direct sync of inventory after unequipping from slot {slot}")

    @Slot(str)
    def on_item_examined(self, item_id):
        """Handle when an item is examined"""
        # Nothing needed here for now, but could be used for tracking item knowledge
        pass

    def toggleRightPanel(self, index):
        """
        Toggle the right panel between collapsed (only tab headers, transparent)
        and expanded (white content area visible, container wider than collapsed state).
        """
        # Recalculate the collapsed width.
        collapsed_width = self.info_tabs.tabBar().sizeHint().width() + 10
        current_width = self.right_panel_container.maximumWidth()
        if current_width == collapsed_width:
            # Expand: change background to white and animate width to expanded_width.
            self.right_panel_container.setStyleSheet("background-color: white;")
            self.animateRightPanel(current_width, self.expanded_width)
        else:
            # Collapse: animate width back to collapsed_width.
            self.animateRightPanel(current_width, collapsed_width)
            from PySide6.QtCore import QTimer
            # After animation, reset background to transparent.
            QTimer.singleShot(300, lambda: self.right_panel_container.setStyleSheet("background: transparent;"))


    def animatePagesContainer(self, start_width, end_width):
        """
        Animate the pages_container's maximumWidth and minimumWidth property.
        """
        from PySide6.QtCore import QPropertyAnimation
        anim = QPropertyAnimation(self.pages_container, b"maximumWidth")
        anim.setDuration(300)
        anim.setStartValue(start_width)
        anim.setEndValue(end_width)
        anim.start()
        self.pages_container.setMinimumWidth(end_width)
        # Retain reference to avoid garbage collection.
        self.pages_container._width_animation = anim


    def animateRightPanel(self, start_width, end_width):
        """
        Animate the right_panel_container's maximumWidth (and set minimumWidth accordingly)
        so that the container expands or collapses.
        """
        from PySide6.QtCore import QPropertyAnimation
        animation = QPropertyAnimation(self.right_panel_container, b"maximumWidth")
        animation.setDuration(300)  # Duration in milliseconds; adjust as needed.
        animation.setStartValue(start_width)
        animation.setEndValue(end_width)
        animation.start()
        # Set the minimum width as well so the container stays fixed.
        self.right_panel_container.setMinimumWidth(end_width)
        # Keep a reference to avoid garbage collection.
        self.right_panel_container._width_animation = animation

    def eventFilter(self, obj, event):
        if obj == self.command_entry and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.on_command_send()
                return True
        return super().eventFilter(obj, event)

    def on_new_game(self):
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtCore import QTimer
        from gui.dialogs import open_new_game_popup, open_save_game_popup

        if self.gm and self.gm.state_manager.state:
            reply = QMessageBox.question(
                self,
                "Save Current Game?",
                "A game is currently in progress. Do you want to manually save the current game before starting a new one?\n\n"
                "Yes: Manual save (opens save dialog).\n"
                "No: Autosave current game.\n"
                "Cancel: Abort starting a new game.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return
            elif reply == QMessageBox.Yes:
                open_save_game_popup(self, self.gm)
            else:
                success, message = self.gm.save_manager.create_save(self.gm.state_manager, "autosave", auto=True)
                if success:
                    self.logger.debug("[DEBUG] Autosave completed.")
                else:
                    self.logger.error("[DEBUG] Autosave failed: " + message)
        
        # Open new game popup without clearing - clearing will happen only after new game is confirmed
        open_new_game_popup(self, self.gm)
        self.update_stats_tab()

    def on_load_game(self):
        from PySide6.QtWidgets import QMessageBox
        if self.gm and self.gm.state_manager.state:
            reply = QMessageBox.question(
                self,
                "Save Current Game?",
                "A game is currently in progress. Do you want to manually save the current game before loading another game?\n\n"
                "Yes: Manual save (opens save dialog).\n"
                "No: Autosave current game.\n"
                "Cancel: Abort loading a new game.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return
            elif reply == QMessageBox.Yes:
                from gui.dialogs import open_save_game_popup
                open_save_game_popup(self, self.gm)
            else:
                success, message = self.gm.save_manager.create_save(self.gm.state_manager, "autosave", auto=True)
                if success:
                    self.logger.debug("[DEBUG] Autosave completed.")
                else:
                    self.logger.error("[DEBUG] Autosave failed: " + message)
            
        # Open load game popup without clearing - clearing will happen only after a game is actually loaded
        from gui.dialogs import open_load_game_popup
        open_load_game_popup(self, self.gm)
        
    def on_save_game(self):
        from gui.dialogs import open_save_game_popup
        open_save_game_popup(self, self.gm)

    def on_settings(self):
        from gui.dialogs import open_settings_popup
        open_settings_popup(self, self.gm)

    def on_quit(self):
        self.input_queue.put("3")
        self.close()

    def on_command_send(self):
        cmd = self.command_entry.toPlainText().strip()
        if cmd:
            # Debug: log the command, the id of the input queue, and its current size
            self.logger.debug(f"on_command_send: Enqueue command: {cmd}")
            self.logger.debug(f"on_command_send: input_queue id: {id(self.input_queue)}; queue size before: {self.input_queue.qsize()}")
            character_name = "Unknown"  # Default name
            if hasattr(self, 'gm') and self.gm.state_manager.state:
                character_name = self.gm.state_manager.state.player.name
            
            userWidget = MessageWidget(character_name, "#000000", self)  # Black color
            # Add italic style to user messages
            styled_cmd = f"<i>{cmd}</i>"  # Make text italic
            userWidget.setMessage(styled_cmd, gradual=False)
            self.conversationWidget.addMessage(userWidget)
            self.input_queue.put(cmd)
            self.command_entry.clear()

    def generate_item_description(self, item):
        """Generate detailed description for an item using LLM if available"""
        if not hasattr(self, 'gm') or not self.gm or not hasattr(self.gm, 'llm_manager'):
            return None
            
        try:
            import asyncio
            from dataclasses import asdict
            from core.agents.base_agent import AgentContext
            
            # Create context for item description
            context = AgentContext(
                current_location=self.gm.state_manager.state.player.location,
                game_state=asdict(self.gm.state_manager.state),
                conversation_history=self.gm.state_manager.state.conversation_history[-10:],  # Last 10 entries
                active_quests=self.gm.state_manager.state.active_quests,
                context_manager=self.gm.state_manager.context_manager,
                context_type="item",
                context_evaluator=self.gm.agents.get("context_evaluator")
            )
            
            # Create specific prompt for item description
            prompt = (
                f"Provide a detailed description for the item '{item.name}'. Include what it looks like, "
                f"any notable features, history or lore if applicable, and how it might be used. "
                f"Format any properties or stats separately. Type: {item.item_type.value}, "
                f"Rarity: {item.rarity.value}"
            )
            
            # Add item stats info
            if item.stats:
                prompt += "\n\nItem has the following stats:\n"
                for stat in item.stats:
                    value = f"{stat.value:+.1f}%" if stat.is_percentage else f"{stat.value:+.1f}"
                    prompt += f"- {stat.name}: {value}\n"
            
            context.game_state["current_input"] = prompt
            
            # Use the narrator agent to generate description
            narrator = self.gm.agents.get("narrator")
            if not narrator:
                return None
                
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # Run the call
            future = asyncio.run_coroutine_threadsafe(narrator.process(context), loop)
            response = future.result(timeout=10.0)  # 10 second timeout
            
            if response.success:
                return response.content
            
            return None
        except Exception as e:
            self.logger.error(f"Error generating item description: {e}")
            return None

    @Slot()        
    def update_output_from_queue(self):
        try:
            while True:
                text = self.output_queue.get_nowait()
                if "[DEBUG]" in text or text.startswith("DEBUG:"):
                    self.tab_debug.setReadOnly(False)
                    self.tab_debug.append(text)
                    self.tab_debug.moveCursor(QTextCursor.End)
                    self.tab_debug.setReadOnly(True)
                else:
                    from gui.message_widget import MessageWidget
                    widget = MessageWidget("System", self.output_color, self)
                    widget.setMessage(text, gradual=False)
                    self.conversationWidget.addMessage(widget)
                # (Optionally, adjust conversationWidget size or call update)
        except queue.Empty:
            pass

    def load_default_theme(self):
        try:
            with open("config/gui_themes.json", "r") as f:
                themes_data = json.load(f)
            default_theme = themes_data["themes"].get("Classic")
            if default_theme:
                # Update overlay tab styling
                if hasattr(self, 'info_tabs'):
                    self.info_tabs.setStyleSheet("""
                        QTabWidget::pane {
                            border: none;
                            background: transparent;
                        }
                        QTabBar::tab {
                            padding: 5px 10px;
                            background: rgba(255, 255, 255, 0.7);
                            border: 1px solid #ccc;
                            border-bottom: none;
                            border-top-left-radius: 4px;
                            border-top-right-radius: 4px;
                        }
                        QTabBar::tab:selected {
                            background: white;
                            margin-bottom: -1px;
                            font-weight: bold;
                        }
                        QTabBar::tab:hover:!selected {
                            background: rgba(255, 255, 255, 0.9);
                        }
                        QTabWidget::tab-bar {
                            alignment: center;
                        }
                    """)
                    
                    # Update tab content fonts
                    font_main = default_theme.get("font_main", ["Garamond", 12])
                    if hasattr(self, 'tab_stats'):
                        self.tab_stats.setFont(QFont(*font_main))
                    if hasattr(self, 'tab_quests'):
                        self.tab_quests.setFont(QFont(*font_main))
                    if hasattr(self, 'tab_inventory'):
                        self.tab_inventory.setFont(QFont(*font_main))
                    if hasattr(self, 'tab_debug'):
                        self.tab_debug.setFont(QFont(*default_theme.get("font_debug", ["Courier", 10])))
                        self.tab_debug.setStyleSheet(f"background-color: {default_theme.get('bg_debug', '#EEE')};")
               
        except Exception as e:
            self.logger.error(f"[DEBUG] Error loading default theme: {e}")

    @Slot()
    def update_stats_tab(self):
        # Check if game manager, state manager, state, and player all exist
        if not self.gm or not self.gm.state_manager or not self.gm.state_manager.state:
            return  # Exit early if any required object is None
            
        if not hasattr(self.gm.state_manager.state, 'player') or not self.gm.state_manager.state.player:
            return  # Exit if player is None
            
        player = self.gm.state_manager.state.player
        
        # Get base stats
        base_stats = player.stats
        
        # Skip modified stats calculation if calculate_stats_with_modifiers not implemented yet
        if hasattr(player, 'calculate_stats_with_modifiers'):
            try:
                modified_stats = player.calculate_stats_with_modifiers()
            except Exception as e:
                self.logger.error(f"Error calculating modified stats: {e}")
                modified_stats = base_stats
        else:
            modified_stats = base_stats
        
        # Calculate derived stats
        try:
            derived = player.compute_derived_stats()
        except Exception as e:
            derived = {}
            self.logger.error(f"[DEBUG] Error computing derived stats: {e}")
                
        # Build character info
        char_info = f"Character: {player.name}\n"
        char_info += f"Race: {player.race}\n"
        char_info += f"Path: {player.path}\n"
        char_info += f"Background: {player.background}\n"
        char_info += f"Level: {player.level}\n"
        char_info += f"Experience: {player.experience}\n\n"
        
        # Build primary stats text with modifiers
        text = char_info
        text += "Primary Attributes (Base + Item Modifiers):\n"
        
        for stat_name in ['STR', 'AGI', 'CON', 'INT', 'WIS', 'CHA']:
            base_value = base_stats.get(stat_name, 'N/A')
            modified_value = modified_stats.get(stat_name, base_value)
            
            # Show both base and modified values if they differ
            if base_value != modified_value:
                text += f"  {stat_name}: {base_value} → {modified_value} "
                # Calculate and show the difference
                if isinstance(base_value, (int, float)) and isinstance(modified_value, (int, float)):
                    diff = modified_value - base_value
                    text += f"({'+' if diff > 0 else ''}{diff})"
                text += "\n"
            else:
                text += f"  {stat_name}: {base_value}\n"
        
        text += "\n"
        
        # Build derived stats text
        text += "Derived Stats:\n"
        text += f"  HP: {derived.get('HP', 'N/A')}\n"
        text += f"  SP: {derived.get('SP', 'N/A')}\n"
        text += f"  MP: {derived.get('MP', 'N/A')}\n"
        text += f"  Social Standing: {derived.get('SS', 'N/A')}\n\n"
        
        # Build combat stats text
        text += "Combat Stats:\n"
        text += f"  Physical Defense: {derived.get('Physical Defense', 0):.1f}\n"
        text += f"  Magic Defense: {derived.get('Magic Defense', 0):.1f}\n"
        text += f"  Initiative: {derived.get('Initiative', 0):.1f}\n"
        
        # Add Equipped Items section safely
        if hasattr(player, 'inventory_data') and player.inventory_data:
            equipped_items = player.inventory_data.get('equipped_items', {})
            if equipped_items:
                text += "\nEquipped Items:\n"
                for slot, item_id in equipped_items.items():
                    if not item_id:
                        continue
                        
                    # Find item details in backpack
                    item_name = "Unknown Item"
                    
                    # If we have access to the inventory manager, use it to get item details
                    if hasattr(self.gm, 'inventory_manager') and self.gm.inventory_manager:
                        try:
                            item = self.gm.inventory_manager.get_item(item_id)
                            if item:
                                item_name = item.name
                        except Exception as e:
                            self.logger.error(f"Error retrieving item from inventory manager: {e}")
                    
                    # Fallback to searching in backpack
                    if item_name == "Unknown Item":
                        try:
                            for backpack_item in player.inventory_data.get('backpack', []):
                                # Handle both string and dictionary items
                                if isinstance(backpack_item, str):
                                    if backpack_item == item_id:
                                        item_name = item_id  # Use ID as name as fallback
                                        break
                                elif isinstance(backpack_item, dict) and backpack_item.get('id') == item_id:
                                    item_name = backpack_item.get('name', 'Unknown Item')
                                    break
                        except Exception as e:
                            self.logger.error(f"Error searching backpack: {e}")
                            
                    text += f"  {slot.replace('_', ' ').title()}: {item_name}\n"
        
        # Update stats tab
        self.tab_stats.setPlainText(text)
               
        # Update quest log using the new quest manager
        if hasattr(self.gm, 'quest_manager'):
            active_quests = self.gm.quest_manager.get_active_quests()
            completed_quests = self.gm.quest_manager.get_completed_quests()
            self.tab_quests.update_quests(active_quests, completed_quests)
        else:
            # Fallback to the old method using active events if quest manager is not available
            if hasattr(self.gm.state_manager.state, 'world') and hasattr(self.gm.state_manager.state.world, 'active_events'):
                active_events = self.gm.state_manager.state.world.active_events
                if active_events:
                    # Create a simple active events representation for the quest list widget
                    event_quests = []
                    for i, event in enumerate(active_events):
                        event_quests.append({
                            "id": f"event_{i}",
                            "name": f"Active Event {i+1}",
                            "description": event,
                            "status": "active",
                            "steps": []
                        })
                    self.tab_quests.update_quests(event_quests, [])
                        
        # After stats are updated, make sure inventory is initialized
        if not hasattr(self.gm, 'inventory_manager'):
            # Create inventory manager if it doesn't exist
            from core.inventory.item_manager import InventoryManager
            self.gm.inventory_manager = InventoryManager(self.gm.config)
            
            # Load inventory data from player state if available
            if (hasattr(self.gm.state_manager.state, 'player') and 
                hasattr(self.gm.state_manager.state.player, 'inventory_data') and 
                self.gm.state_manager.state.player.inventory_data):
                self.gm.inventory_manager.from_dict(self.gm.state_manager.state.player.inventory_data)
            else:
                # Add some default starter items
                self.gm.inventory_manager.add_item("item_copper_sword")
                self.gm.inventory_manager.add_item("item_leather_boots")
                self.gm.inventory_manager.add_item("item_health_potion", 3)
        
        # Initialize inventory widget if needed
        self.initialize_inventory_widget()

    @Slot(object, str)
    def check_summary_future(self, future, expected_session):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.gm._check_summary_future(future, expected_session))


    @Slot(str)
    def append_to_output(self, text: str):
        widget = MessageWidget("System", self.output_color, self)
        widget.setMessage(text, gradual=False)
        self.conversationWidget.addMessage(widget)

    def append_debug_output(self, text: str):
        """Appends the given text to the Debug tab."""
        self.tab_debug.setReadOnly(False)
        self.tab_debug.append(text)
        self.tab_debug.moveCursor(QTextCursor.End)
        self.tab_debug.setReadOnly(True)

    def append_message(self, message: str, sender: str):
        """
        Append a message to the conversation log with formatting based on sender.
        sender: 'User', 'GameMaster', or 'Context'
        """
        if sender.lower() == "user":
            color = "#EDCFAF"
        else:
            color = "#F1D6B2"
        widget = MessageWidget(sender, color, self)
        widget.setMessage(message, gradual=False)
        self.conversationWidget.addMessage(widget)

    def _tokenize_html(self, text: str) -> list:
        """
        Tokenize an HTML string into a list of tokens.
        Each token is either an HTML tag (e.g. "<strong>") or a text fragment (including trailing whitespace).
        """
        import re
        pattern = re.compile(r'(<[^>]+>)')
        tokens = []
        parts = pattern.split(text)
        for part in parts:
            if not part:
                continue
            if part.startswith("<") and part.endswith(">"):
                tokens.append(part)
            else:
                # Split the text part into tokens (words plus any trailing whitespace)
                tokens.extend(re.findall(r'\S+\s*', part))
        return tokens

    def on_music_play_pause(self):
        """Toggle music playback based on current state"""
        if hasattr(self, 'music_manager'):
            # Get the actual current state
            info = self.music_manager.get_current_track_info()
            current_status = info.get("status", "stopped")
            
            # Toggle based on current status
            if current_status == "playing":
                self.music_manager.pause()
                self.logger.debug("Pausing music playback")
            else:
                self.music_manager.play()
                self.logger.debug("Starting music playback")

    def on_music_next(self):
        self.music_manager.next_track()

    def on_music_previous(self):
        self.music_manager.next_track()  # We'll use next since tracks are randomized

    def on_music_mute(self):
        self.music_manager.toggle_mute()

    def on_music_volume(self, value):
        self.music_manager.set_volume(value)

    def closeEvent(self, event):
        # First, cancel all running tasks in the event loop to avoid race conditions
        if hasattr(self, 'gm') and self.gm:
            try:
                # Cancel any pending API tasks
                if hasattr(self.gm, 'pending_api_task') and self.gm.pending_api_task:
                    self.gm.pending_api_task.cancel()
                
                # Set running state to False to prevent new tasks
                if hasattr(self.gm, 'is_running'):
                    self.gm.is_running = False
                
                if hasattr(self.gm, 'game_loop') and self.gm.game_loop:
                    self.gm.game_loop.is_running = False
                    
                # Explicitly call cleanup
                if hasattr(self.gm, 'cleanup_on_exit'):
                    self.gm.cleanup_on_exit()
                    
                # Give tasks a small chance to terminate gracefully
                import time
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error during exit cleanup: {e}")
        
        # Clean up music manager before closing
        if hasattr(self, 'music_manager'):
            self.music_manager.cleanup()
        
        super().closeEvent(event)

    def assign_gui_to_llm_manager(self):
        """Assign GUI reference to LLMManager and apply music settings"""
        if hasattr(self, 'gm') and self.gm:
            # First set music manager reference to avoid errors
            if hasattr(self, 'music_manager') and self.gm.llm_manager:
                self.gm.llm_manager.gui = self
                self.logger.info(f"Assigned GameGUI to LLMManager.gui")
                
                # Apply music settings from config now that game manager is available
                self.apply_music_settings_from_config()
            else:
                self.logger.warning("Music manager not initialized yet or LLM manager missing")
                # Try again after a delay
                QTimer.singleShot(1000, self.assign_gui_to_llm_manager)
        else:
            self.logger.warning("Game manager not available yet, will retry")
            # Try again after a delay
            QTimer.singleShot(1000, self.assign_gui_to_llm_manager)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = GameGUI()
    gui.show()
    sys.exit(app.exec())
