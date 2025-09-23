#!/usr/bin/env python3
"""
Web server for the RPG game using FastAPI.
Provides API endpoints and WebSocket functionality to interface with the game engine.
"""

import os
import sys
import json
import uuid
import logging
import asyncio
from typing import Dict, List, Optional, Any
# Import datetime directly - CRITICAL - must be at global level for exec() to work
from datetime import datetime

# Define datetime at global level to make it available to exec() context
datetime = datetime  # Redefine to ensure it's in the global namespace

# Add the project root to the path to import core modules
# Ensure we can find project root from any execution context
server_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(server_dir)
project_root = os.path.dirname(web_dir)

# Insert project root at beginning of path to ensure correct imports
sys.path.insert(0, project_root)

# Print path for debugging
print(f"Project root: {project_root}")
print(f"Python path: {sys.path}")

# FastAPI imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.responses import JSONResponse

# Import Pydantic BaseModel
from pydantic import BaseModel, Field

# Game engine imports
from core.base.engine import GameEngine
from core.base.state import GameState, PlayerState, WorldState
from core.base.commands import CommandResult
from core.utils.logging_config import get_logger
from core.llm.settings_manager import SettingsManager

# Configure logger
logger = get_logger("API")

# Active game sessions - mapping session_id to GameEngine instance
active_sessions: Dict[str, GameEngine] = {}

# Active WebSocket connections - mapping session_id to list of WebSocket connections
websocket_connections: Dict[str, List[WebSocket]] = {}

# Session listeners to allow disconnecting/cleanup per session
session_listeners: Dict[str, Dict[str, Any]] = {}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path

# Get path to web client files
# Try multiple approaches to find the client directory
possible_paths = []

# First approach: Try using current working directory
cwd = os.getcwd()
client_dir_cwd = Path(cwd).joinpath('web', 'client')
possible_paths.append(("CWD", client_dir_cwd))

# Second approach: Try using relative path from server.py location
server_dir = Path(os.path.abspath(__file__)).parent
parent_dir = server_dir.parent.parent  # Go up two levels from server.py
client_dir_relative = parent_dir.joinpath('web', 'client')
possible_paths.append(("Relative", client_dir_relative))

# Check if any of the paths exist
client_dir = None
for path_type, path in possible_paths:
    logger.info(f"Trying to locate client directory using {path_type} approach: {path}")
    if path.exists():
        client_dir = path
        logger.info(f"Found client directory at: {client_dir}")
        break

# If no client directory found, raise an error
if client_dir is None:
    error_msg = f"Client directory not found. Tried the following paths: {[str(p[1]) for p in possible_paths]}"
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)

# Create FastAPI application
app = FastAPI(
    title="RPG Game API",
    description="API for the RPG game web interface",
    version="0.1.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory - multiple mounts to handle different path references
app.mount("/static", StaticFiles(directory=str(client_dir)), name="static")
# Mount CSS and JS directories directly to support references without /static/ prefix
app.mount("/css", StaticFiles(directory=str(client_dir / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(client_dir / "js")), name="js")
# Root path redirects to the web client
@app.get("/")
async def root():
    return FileResponse(str(client_dir / "index.html"))

# Helper function to scan for character icons
def get_character_icons():
    """Scan for character icons in the images/character_icons directory (flat)."""
    icons_dir = os.path.join(project_root, "images", "character_icons")
    os.makedirs(icons_dir, exist_ok=True)
    supported_extensions = [".png", ".jpg", ".jpeg", ".gif", ".svg"]
    icons = []
    try:
        for filename in os.listdir(icons_dir):
            if any(filename.lower().endswith(ext) for ext in supported_extensions):
                file_path = os.path.join(icons_dir, filename)
                url_path = f"/images/character_icons/{filename}"
                icons.append({"filename": filename, "path": file_path, "url": url_path})
    except Exception:
        pass
    icons.sort(key=lambda x: x["filename"]) 
    return icons

def get_character_icons_filtered(race: Optional[str], class_name: Optional[str], sex: Optional[str]):
    """Scan for icons in subfolder images/character_icons/<Race_Class> and filter by sex keywords."""
    from pathlib import Path
    safe_race = (race or "").replace(" ", "_")
    safe_class = (class_name or "").replace(" ", "_")
    base_dir = Path(project_root) / "images" / "character_icons"
    subdir = base_dir / f"{safe_race}_{safe_class}"
    supported = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
    results: List[Dict[str, str]] = []
    if not safe_race or not safe_class:
        return results
    try:
        if not subdir.exists():
            return results
        sex_l = (sex or "").lower()
        for p in sorted(subdir.iterdir()):
            if p.is_file() and p.suffix.lower() in supported:
                name_lower = p.stem.lower()
                contains_male = "male" in name_lower
                contains_female = "female" in name_lower
                include = False
                if sex_l == "male":
                    include = contains_male and not contains_female
                elif sex_l == "female":
                    include = contains_female
                else:
                    include = contains_male or contains_female
                if include:
                    rel = f"/images/character_icons/{safe_race}_{safe_class}/{p.name}"
                    results.append({"filename": p.name, "path": str(p), "url": rel})
    except Exception as e:
        logger.warning(f"Error scanning filtered character icons: {e}")
    return results

# Mount images directory for character icons
try:
    images_dir = os.path.join(project_root, "images")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(os.path.join(images_dir, "character_icons"), exist_ok=True)
    app.mount("/images", StaticFiles(directory=images_dir), name="images")
    logger.info(f"Mounted images directory at: {images_dir}")
except Exception as e:
    logger.error(f"Error mounting images directory: {e}")

# Simple OAuth2 password bearer for basic authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Model for creating a new game
class NewGameRequest(BaseModel):
    player_name: str = Field(..., description="Name of the player character")
    race: str = Field(default="Human", description="Race of the player character")
    path: str = Field(default="Wanderer", description="Class/path of the player character")
    background: str = Field(default="Commoner", description="Background/backstory seed (Origin description)")
    sex: str = Field(default="Male", description="Sex/gender of the player character")
    character_image: Optional[str] = Field(None, description="Path to character portrait image")
    use_llm: bool = Field(default=True, description="Whether to enable LLM functionality for this game")
    origin_id: Optional[str] = Field(default=None, description="Selected Origin ID")
    stats: Optional[Dict[str, int]] = Field(default=None, description="Allocated base stats mapping (e.g., {'STR':12,...})")
    
# Model for session information
class SessionInfo(BaseModel):
    session_id: str = Field(..., description="Unique game session ID")
    player_name: str = Field(..., description="Player character name")
    created_at: datetime = Field(..., description="Session creation time")
    race: Optional[str] = Field(None, description="Player character race")
    path: Optional[str] = Field(None, description="Player character class/path")
    background: Optional[str] = Field(None, description="Player character background")
    sex: Optional[str] = Field(None, description="Player character sex/gender")
    character_image: Optional[str] = Field(None, description="Path to character portrait image")
    llm_enabled: bool = Field(False, description="Whether LLM functionality is enabled")
    location: Optional[str] = Field(None, description="Current location")
    game_time: Optional[str] = Field(None, description="Current in-game time")
    
# Model for command request
class CommandRequest(BaseModel):
    command: str  # Game command to execute
    
# Model for save game request
class SaveGameRequest(BaseModel):
    save_name: Optional[str] = None  # Name for the save file

# Model for load game request
class LoadGameRequest(BaseModel):
    save_id: str  # ID of the save to load

# UI State response models (lightweight)
class UIResourceBar(BaseModel):
    current: float
    max: float

class UIPlayerHeader(BaseModel):
    name: str
    race: str
    path: str
    level: int = 1
    experience_current: int = 0
    experience_max: int = 100
    sex: Optional[str] = None
    portrait_url: Optional[str] = None

class UIStatEntry(BaseModel):
    name: str
    value: float
    base_value: float

class UIEquipmentEntry(BaseModel):
    slot: str
    item_id: Optional[str] = None
    item_name: Optional[str] = None

class UIStatusEffectEntry(BaseModel):
    name: str
    duration: Optional[int] = None

class UIStateResponse(BaseModel):
    mode: str
    location: Optional[str] = None
    time: Optional[str] = None
    player: UIPlayerHeader
    resources: Dict[str, UIResourceBar]
    primary_stats: Dict[str, UIStatEntry]
    derived_stats: Dict[str, UIStatEntry]
    social_stats: Dict[str, UIStatEntry]
    other_stats: Dict[str, UIStatEntry]
    status_effects: List[UIStatusEffectEntry] = []
    equipment: List[UIEquipmentEntry] = []
    turn_order: List[str] = []
    initiative: Optional[float] = None
    journal: Dict[str, Any] = {}
    
# Model for save information
class SaveInfo(BaseModel):
    save_id: str  # Save ID
    save_name: str  # Save name
    save_time: datetime  # Save creation time
    player_name: str  # Player character name
    player_level: int  # Player character level
    location: str  # Current location

# Models for LLM settings management
class ProviderSettings(BaseModel):
    api_key: str = Field(default="", description="API key for the provider")
    organization_id: Optional[str] = Field(default="", description="Organization ID (if applicable)")
    enabled: bool = Field(default=True, description="Whether this provider is enabled")

class ProviderConfig(BaseModel):
    openai: ProviderSettings
    google: ProviderSettings
    openrouter: ProviderSettings

class AgentSettings(BaseModel):
    provider_type: str = Field(description="Provider type for this agent")
    model: str = Field(description="Model to use for this agent")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    top_p: float = Field(default=1.0, description="Top-p sampling value")
    max_tokens: int = Field(default=1000, description="Maximum tokens to generate")
    enabled: bool = Field(default=True, description="Whether this agent is enabled")

class AgentConfig(BaseModel):
    narrator: AgentSettings
    rule_checker: AgentSettings
    context_evaluator: AgentSettings

class LLMSettingsResponse(BaseModel):
    providers: ProviderConfig
    agents: AgentConfig
    llm_enabled: bool = Field(description="Whether LLM functionality is enabled")

class ToggleLLMRequest(BaseModel):
    enabled: bool = Field(description="Whether to enable LLM functionality")
    
# Simple user database for demonstration
# In a real application, use a proper database and password hashing
USERS = {
    "admin": {
        "username": "admin",
        "password": "adminpassword",  # Use hashed passwords in production
        "disabled": False,
    }
}

# Character icon model
class CharacterIcon(BaseModel):
    filename: str = Field(..., description="Filename of the icon")
    path: str = Field(..., description="Path to the icon file")
    url: str = Field(..., description="URL to access the icon")

# Authentication dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current user from the token."""
    # In a real application, validate the JWT token
    # For demonstration, we'll just check if the token is a username in our database
    if token not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = USERS[token]
    if user.get("disabled"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Session validation dependency
async def get_game_engine(session_id: str = None):
    """Get the game engine for a session."""
    # For endpoints that require session ID in path
    if session_id:
        if session_id not in active_sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game session {session_id} not found",
            )
        return active_sessions[session_id]
    # For endpoints that should work without a session
    return None

# Authentication endpoint
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint for obtaining access token."""
    user = USERS.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # In a real application, return a JWT token
    # For demonstration, we'll just return the username as the token
    return {"access_token": user["username"], "token_type": "bearer"}

# WebSocket connection manager for real-time game updates
class ConnectionManager:
    """
    Manages WebSocket connections for real-time game updates.
    """
    
    @staticmethod
    async def connect(websocket: WebSocket, session_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        if session_id not in websocket_connections:
            websocket_connections[session_id] = []
        websocket_connections[session_id].append(websocket)
        logger.info(f"WebSocket connected for session {session_id}")
    
    @staticmethod
    async def disconnect(websocket: WebSocket, session_id: str):
        """Disconnect a WebSocket client."""
        if session_id in websocket_connections and websocket in websocket_connections[session_id]:
            websocket_connections[session_id].remove(websocket)
            logger.info(f"WebSocket disconnected for session {session_id}")
    
    @staticmethod
    async def send_update(session_id: str, data: dict):
        """Send an update to all WebSocket clients for a session."""
        if session_id in websocket_connections:
            disconnected = []
            for websocket in websocket_connections[session_id]:
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    logger.error(f"Error sending WebSocket update: {e}")
                    disconnected.append(websocket)
            
            # Remove disconnected WebSockets
            for websocket in disconnected:
                if websocket in websocket_connections[session_id]:
                    websocket_connections[session_id].remove(websocket)

# WebSocket endpoint for real-time game updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time game updates."""
    await ConnectionManager.connect(websocket, session_id)
    try:
        # Send initial game state
        if session_id in active_sessions:
            engine = active_sessions[session_id]
            state = engine.state_manager.state
            await websocket.send_json({
                "type": "game_state",
                "data": {
                    "player": {
                        "name": state.player.name,
                        "level": state.player.level,
                        "location": state.world.current_location
                    },
                    "time": state.game_time.get_formatted_time(),
                    "game_running": engine.game_loop.is_running,
                }
            })
        
        # Listen for WebSocket messages
        while True:
            # This will keep the connection open and handle disconnections
            data = await websocket.receive_text()
            # Process any WebSocket commands if needed
            # For now, we'll just use HTTP endpoints for commands
    except WebSocketDisconnect:
        await ConnectionManager.disconnect(websocket, session_id)

# API endpoints

# Helper to attach engine listeners for a session
def _attach_engine_listeners(session_id: str, engine: GameEngine):
    """Attach engine signals to websocket broadcast for the given session."""
    # Clean existing listeners
    try:
        if session_id in session_listeners:
            lst = session_listeners.pop(session_id)
            # Attempt to disconnect prior connections if present
            try:
                if lst.get('stats_conn') and engine.state_manager.stats_manager:
                    engine.state_manager.stats_manager.stats_changed.disconnect(lst['stats_conn'])
            except Exception:
                pass
            try:
                if lst.get('orch_conn'):
                    engine.orchestrated_event_to_ui.disconnect(lst['orch_conn'])
            except Exception:
                pass
    except Exception:
        pass

    def _emit_ws(payload: dict):
        try:
            asyncio.create_task(ConnectionManager.send_update(session_id, payload))
        except Exception as e:
            logger.warning(f"WS emit failed: {e}")

    # Stats changed -> broadcast
    def on_stats_changed(stats_data):
        _emit_ws({"type": "stats_changed", "data": stats_data})
    stats_conn = None
    try:
        if engine.state_manager and engine.state_manager.stats_manager:
            engine.state_manager.stats_manager.stats_changed.connect(on_stats_changed)
            stats_conn = on_stats_changed
    except Exception as e:
        logger.warning(f"Failed connecting stats_changed listener: {e}")

    # Orchestrated events -> broadcast specific types
    from core.orchestration.events import DisplayEvent, DisplayEventType
    def on_orchestrated_event(event_obj):
        try:
            if not isinstance(event_obj, DisplayEvent):
                return
            t = event_obj.type
            # Map to websocket event types
            if t == DisplayEventType.TURN_ORDER_UPDATE:
                _emit_ws({"type": "turn_order_update", "data": event_obj.content})
            elif t == DisplayEventType.UI_BAR_UPDATE_PHASE1:
                _emit_ws({"type": "ui_bar_update_phase1", "data": event_obj.metadata or {}})
            elif t == DisplayEventType.UI_BAR_UPDATE_PHASE2:
                _emit_ws({"type": "ui_bar_update_phase2", "data": event_obj.metadata or {}})
            elif t == DisplayEventType.COMBAT_LOG_SET_HTML:
                _emit_ws({"type": "combat_log_set_html", "data": {"html": event_obj.content}})
            elif t in (DisplayEventType.SYSTEM_MESSAGE, DisplayEventType.NARRATIVE_GENERAL, DisplayEventType.NARRATIVE_ATTEMPT, DisplayEventType.NARRATIVE_IMPACT):
                _emit_ws({"type": "narrative", "data": {"role": event_obj.role or "system", "text": event_obj.content, "gradual": bool(event_obj.gradual_visual_display)}})
            # else: ignore other internal events
        except Exception as e:
            logger.warning(f"Error handling orchestrated event for WS: {e}")
    orch_conn = None
    try:
        engine.orchestrated_event_to_ui.connect(on_orchestrated_event)
        orch_conn = on_orchestrated_event
    except Exception as e:
        logger.warning(f"Failed connecting orchestrator listener: {e}")

    session_listeners[session_id] = {"stats_conn": stats_conn, "orch_conn": orch_conn}

@app.post("/api/new_game", response_model=SessionInfo)
async def create_new_game(request: NewGameRequest):
    """Create a new game session."""
    try:
        session_id = str(uuid.uuid4())
        engine = GameEngine()
        # Start new game using full parameters
        engine.start_new_game(
            player_name=request.player_name,
            race=request.race,
            path=request.path,
            background=request.background,
            sex=request.sex,
            character_image=request.character_image,
            stats=request.stats,
            origin_id=request.origin_id
        )
        # Toggle LLM
        engine.set_llm_enabled(request.use_llm)
        # Store in active sessions
        active_sessions[session_id] = engine
        websocket_connections[session_id] = []
        # Attach listeners for this session
        _attach_engine_listeners(session_id, engine)
        logger.info(f"Created new game session {session_id} for player {request.player_name}")
        state = engine.state_manager.state
        return SessionInfo(
            session_id=session_id,
            player_name=request.player_name,
            created_at=datetime.now(),
            race=state.player.race,
            path=state.player.path,
            background=state.player.background,
            sex=state.player.sex,
            character_image=state.player.character_image,
            llm_enabled=engine._use_llm,
            location=state.player.current_location,
            game_time=state.game_time.get_formatted_time() if state else None
        )
    except Exception as e:
        logger.error(f"Error creating new game: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating new game: {str(e)}"
        )

@app.post("/api/command/{session_id}")
async def process_command(session_id: str, request: CommandRequest, engine: GameEngine = Depends(get_game_engine)):
    """Process a game command."""
    try:
        # Process the command using the game engine
        result = engine.process_command(request.command)
        
        # Get the updated game state
        state = engine.state_manager.state
        
        # Prepare response data
        response_data = {
            "status": result.status.name,
            "message": result.message,
            "data": result.data or {},
            "state": {
                "player": {
                    "name": state.player.name,
                    "level": state.player.level,
                    "location": state.world.current_location
                },
                "time": state.game_time.get_formatted_time(),
                "game_running": engine.game_loop.is_running,
            }
        }
        
        # Add a marker to the message to prevent duplicate display
        response_data["source"] = "http_response"
        
        # Send update to WebSocket clients only for events that should be broadcast
        # This prevents duplicate outputs when using LLM commands
        if result.status.name != "SUCCESS" or "websocket_sent" not in result.data:
            # Mark that we've broadcast this via websocket
            if not result.data:
                result.data = {}
            result.data["websocket_sent"] = True
            
            # Create a websocket-specific copy of the data
            ws_data = response_data.copy()
            ws_data["source"] = "websocket"
            
            # Send via websocket
            asyncio.create_task(ConnectionManager.send_update(session_id, {
                "type": "command_result",
                "data": ws_data
            }))
        
        return response_data
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing command: {str(e)}"
        )

@app.post("/api/save_game/{session_id}")
async def save_game(session_id: str, request: SaveGameRequest, engine: GameEngine = Depends(get_game_engine)):
    """Save the current game state."""
    try:
        # Generate save ID and name
        save_id = str(uuid.uuid4())
        save_name = request.save_name or f"Save_{engine.state_manager.state.player.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save the game
        engine.state_manager.save_game(save_id)
        
        # Update metadata
        from core.utils.save_manager import SaveManager
        save_manager = SaveManager()
        state = engine.state_manager.state
        
        save_manager.update_metadata(
            save_id=save_id,
            updates={
                "save_name": save_name,
                "player_name": state.player.name,
                "player_level": state.player.level,
                "world_time": state.game_time.get_formatted_time(),
                "location": state.world.current_location,
                "playtime": state.playtime
            }
        )
        
        logger.info(f"Saved game {save_id} for session {session_id}")
        
        return {
            "status": "success",
            "message": f"Game saved as '{save_name}'",
            "save_id": save_id,
            "save_name": save_name
        }
    except Exception as e:
        logger.error(f"Error saving game: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving game: {str(e)}"
        )

@app.post("/api/load_game/{session_id}")
async def load_game(session_id: str, request: LoadGameRequest, engine: GameEngine = Depends(get_game_engine)):
    """Load a saved game state."""
    try:
        # Load the game
        success = engine.state_manager.load_game(request.save_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Save file with ID {request.save_id} not found or is invalid"
            )
        
        # Get the updated game state
        state = engine.state_manager.state
        
        # Prepare response data
        response_data = {
            "status": "success",
            "message": "Game loaded successfully",
            "state": {
                "player": {
                    "name": state.player.name,
                    "level": state.player.level,
                    "location": state.world.current_location
                },
                "time": state.game_time.get_formatted_time(),
                "game_running": engine.game_loop.is_running,
            }
        }
        
        # Attach listeners (in case engine was recreated/reset by load) and send update
        try:
            _attach_engine_listeners(session_id, engine)
        except Exception:
            pass
        asyncio.create_task(ConnectionManager.send_update(session_id, {
            "type": "game_loaded",
            "data": response_data
        }))
        
        logger.info(f"Loaded game {request.save_id} for session {session_id}")
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading game: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading game: {str(e)}"
        )

@app.get("/api/ui/state/{session_id}", response_model=UIStateResponse)
async def get_ui_state(session_id: str, engine: GameEngine = Depends(get_game_engine)):
    """Aggregate UI state for the right panel and status bar to mimic Py GUI."""
    try:
        state = engine.state_manager.state
        if not state:
            raise HTTPException(status_code=404, detail="No active state")

        # Player header
        player = state.player
        sm = engine.state_manager.stats_manager
        level = getattr(sm, 'level', 1) if sm else 1
        header = UIPlayerHeader(
            name=getattr(player, 'name', 'Unknown'),
            race=getattr(player, 'race', 'Unknown'),
            path=getattr(player, 'path', 'Unknown'),
            level=level,
            sex=getattr(player, 'sex', None),
            experience_current=0,
            experience_max=100,
            portrait_url=getattr(player, 'character_image', None)
        )

        # Resources
        resources: Dict[str, UIResourceBar] = {}
        if sm:
            from core.stats.stats_base import DerivedStatType
            def rb(current_t, max_t):
                cur = sm.get_current_stat_value(current_t)
                mx = sm.get_stat_value(max_t)
                return UIResourceBar(current=cur, max=mx)
            resources['health'] = rb(DerivedStatType.HEALTH, DerivedStatType.MAX_HEALTH)
            resources['mana'] = rb(DerivedStatType.MANA, DerivedStatType.MAX_MANA)
            resources['stamina'] = rb(DerivedStatType.STAMINA, DerivedStatType.MAX_STAMINA)

        # Stats
        primary_stats: Dict[str, UIStatEntry] = {}
        derived_stats: Dict[str, UIStatEntry] = {}
        social_stats: Dict[str, UIStatEntry] = {}
        other_stats: Dict[str, UIStatEntry] = {}
        if sm:
            all_stats = sm.get_all_stats()
            for key, data in (all_stats.get('primary') or {}).items():
                primary_stats[key] = UIStatEntry(name=str(data.get('name', key)), value=float(data.get('value', 0)), base_value=float(data.get('base_value', 0)))
            for key, data in (all_stats.get('combat') or {}).items():
                derived_stats[key] = UIStatEntry(name=str(data.get('name', key)), value=float(data.get('value', 0)), base_value=float(data.get('base_value', 0)))
            for key, data in (all_stats.get('social') or {}).items():
                social_stats[key] = UIStatEntry(name=str(data.get('name', key)), value=float(data.get('value', 0)), base_value=float(data.get('base_value', 0)))
            for key, data in (all_stats.get('other') or {}).items():
                other_stats[key] = UIStatEntry(name=str(data.get('name', key)), value=float(data.get('value', 0)), base_value=float(data.get('base_value', 0)))

        # Status effects
        status_effects: List[UIStatusEffectEntry] = []
        if sm and hasattr(sm, 'get_status_effects'):
            for eff in sm.get_status_effects():
                try:
                    status_effects.append(UIStatusEffectEntry(name=getattr(eff, 'name', 'Effect'), duration=getattr(eff, 'remaining_turns', None)))
                except Exception:
                    continue

        # Equipment
        from core.inventory.item_manager import get_inventory_manager
        inv = get_inventory_manager()
        equipment_entries: List[UIEquipmentEntry] = []
        try:
            eq = getattr(inv, 'equipment', {})
            for slot, item_id in eq.items():
                slot_name = slot.value if hasattr(slot, 'value') else str(slot)
                item_name = None
                if item_id:
                    item = inv.get_item(item_id)
                    item_name = getattr(item, 'name', None)
                equipment_entries.append(UIEquipmentEntry(slot=slot_name, item_id=item_id, item_name=item_name))
        except Exception:
            pass

        # Mode, location, time
        mode = getattr(state.current_mode, 'name', str(getattr(state, 'current_mode', 'NARRATIVE')))
        location = getattr(player, 'current_location', None)
        game_time = state.game_time.get_formatted_time() if getattr(state, 'game_time', None) else None

        # Combat info (basic)
        turn_order: List[str] = []
        initiative = None
        try:
            cm = getattr(state, 'combat_manager', None)
            if cm and mode == 'COMBAT':
                # If combat manager exposes turn order list of names
                order = getattr(cm, 'turn_order', [])
                turn_order = [str(getattr(e, 'name', e)) for e in order] if isinstance(order, list) else []
                initiative = None
        except Exception:
            pass

        journal = getattr(state, 'journal', {}) or {}

        return UIStateResponse(
            mode=mode,
            location=location,
            time=game_time,
            player=header,
            resources=resources,
            primary_stats=primary_stats,
            derived_stats=derived_stats,
            social_stats=social_stats,
            other_stats=other_stats,
            status_effects=status_effects,
            equipment=equipment_entries,
            turn_order=turn_order,
            initiative=initiative,
            journal=journal,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building UI state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error building UI state")


@app.get("/api/inventory/{session_id}")
async def get_inventory_state(session_id: str, engine: GameEngine = Depends(get_game_engine)):
    """Return inventory listing, equipped flags, and currency/weight."""
    try:
        from core.inventory.item_manager import get_inventory_manager
        inv = get_inventory_manager()
        items = []
        for item in getattr(inv, 'items', []):
            try:
                items.append({
                    'id': item.id,
                    'name': item.name,
                    'type': item.item_type.value if hasattr(item.item_type, 'value') else str(item.item_type),
                    'description': getattr(item, 'description', ''),
                    'count': getattr(item, 'quantity', 1),
                    'equipped': bool(inv.is_item_equipped(item.id))
                })
            except Exception:
                continue
        currency = getattr(inv, 'currency', None)
        money = {'gold': 0, 'silver': 0, 'copper': 0}
        if currency:
            money['gold'] = getattr(currency, 'gold', 0)
            money['silver'] = getattr(currency, 'silver', 0)
            total_copper = getattr(currency, '_copper', 0)
            cps = getattr(currency, '_copper_per_silver', 100)
            money['copper'] = total_copper % cps
        current_weight = getattr(inv, 'get_current_weight', lambda: 0.0)()
        weight_limit = getattr(inv, 'weight_limit', 0.0)
        return {
            'items': items,
            'currency': money,
            'weight': {'current': current_weight, 'max': weight_limit}
        }
    except Exception as e:
        logger.error(f"Inventory state error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Inventory state error")


class InventoryActionRequest(BaseModel):
    item_id: Optional[str] = None

    slot: Optional[str] = None
@app.post("/api/inventory/equip/{session_id}")
async def api_inventory_equip(session_id: str, req: InventoryActionRequest, engine: GameEngine = Depends(get_game_engine)):
    if not req.item_id:
        raise HTTPException(status_code=400, detail="item_id required")
    # Use command router like the desktop GUI does
    slot_part = f" {req.slot}" if req.slot else ""
    result = engine.process_command(f"equip {req.item_id}{slot_part}")
    return {
        'status': result.status.name,
        'message': result.message,
        'state_updated': True
    }

@app.post("/api/inventory/unequip/{session_id}")
async def api_inventory_unequip(session_id: str, req: InventoryActionRequest, engine: GameEngine = Depends(get_game_engine)):
    if not req.slot and not req.item_id:
        raise HTTPException(status_code=400, detail="slot or item_id required")
    arg = req.slot or req.item_id
    result = engine.process_command(f"unequip {arg}")
    return {'status': result.status.name, 'message': result.message, 'state_updated': True}

@app.post("/api/inventory/use/{session_id}")
async def api_inventory_use(session_id: str, req: InventoryActionRequest, engine: GameEngine = Depends(get_game_engine)):
    if not req.item_id:
        raise HTTPException(status_code=400, detail="item_id required")
    result = engine.process_command(f"use {req.item_id}")
    return {'status': result.status.name, 'message': result.message, 'state_updated': True}

@app.post("/api/inventory/drop/{session_id}")
async def api_inventory_drop(session_id: str, req: InventoryActionRequest, engine: GameEngine = Depends(get_game_engine)):
    if not req.item_id:
        raise HTTPException(status_code=400, detail="item_id required")
    result = engine.process_command(f"drop {req.item_id}")
    return {'status': result.status.name, 'message': result.message, 'state_updated': True}


# Item details endpoint for Examine dialog
@app.get("/api/items/{session_id}/{item_id}")
async def get_item_details(session_id: str, item_id: str, engine: GameEngine = Depends(get_game_engine)):
    try:
        from core.inventory.item_manager import get_inventory_manager
        inv = get_inventory_manager()
        item = inv.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        # Build a rich detail dict
        def to_name(val):
            try:
                return val.name if hasattr(val, 'name') else str(val)
            except Exception:
                return str(val)
        details: Dict[str, Any] = {
            'id': getattr(item, 'id', None),
            'name': getattr(item, 'name', '?'),
            'item_type': getattr(getattr(item, 'item_type', None), 'value', str(getattr(item, 'item_type', '?'))),
            'description': getattr(item, 'description', ''),
            'weight': getattr(item, 'weight', None),
            'value': getattr(item, 'value', None),
            'quantity': getattr(item, 'quantity', 1),
            'is_stackable': getattr(item, 'is_stackable', False),
            'stack_limit': getattr(item, 'stack_limit', None),
            'durability': getattr(item, 'durability', None),
            'current_durability': getattr(item, 'current_durability', None),
            'equip_slots': [getattr(s, 'value', str(s)) for s in (getattr(item, 'equip_slots', []) or [])],
            'rarity': getattr(getattr(item, 'rarity', None), 'value', None),
            'tags': list(getattr(item, 'tags', []) or []),
            'custom_properties': dict(getattr(item, 'custom_properties', {}) or {}),
            'known_properties': list(getattr(item, 'known_properties', []) or []),
        }
        # Stats/effects if present
        stats_list = []
        try:
            for st in getattr(item, 'stats', []) or []:
                stats_list.append({
                    'name': getattr(st, 'name', None),
                    'display_name': getattr(st, 'display_name', None),
                    'value': getattr(st, 'value', None),
                    'is_percentage': getattr(st, 'is_percentage', False)
                })
        except Exception:
            pass
        details['stats'] = stats_list
        dice_list = []
        try:
            for eff in getattr(item, 'dice_roll_effects', []) or []:
                dice_list.append({
                    'dice_notation': getattr(eff, 'dice_notation', None),
                    'effect_type': getattr(eff, 'effect_type', None),
                    'description': getattr(eff, 'description', None)
                })
        except Exception:
            pass
        details['dice_roll_effects'] = dice_list
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting item details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting item details")

@app.get("/api/list_saves")
async def list_saves():
    """List all available saved games."""
    try:
        from core.utils.save_manager import SaveManager
        save_manager = SaveManager()
        saves = save_manager.get_save_list()
        
        # Convert to response format
        save_list = []
        for save in saves:
            save_list.append({
                "save_id": save.save_id,
                "save_name": save.save_name,
                "save_time": save.save_time,
                "formatted_save_time": save.formatted_save_time,
                "player_name": save.player_name,
                "player_level": save.player_level,
                "location": save.location,
                "world_time": save.world_time
            })
        
        return {
            "status": "success",
            "saves": save_list
        }
    except Exception as e:
        logger.error(f"Error listing saves: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing saves: {str(e)}"
        )

@app.delete("/api/end_session/{session_id}")
async def end_session(session_id: str, engine: GameEngine = Depends(get_game_engine)):
    """End a game session and clean up resources."""
    try:
        # Stop the game loop if running
        if engine.game_loop.is_running:
            engine.game_loop.stop()
        
        # Remove from active sessions
        if session_id in active_sessions:
            del active_sessions[session_id]
        # Disconnect listeners
        try:
            if session_id in session_listeners:
                lst = session_listeners.pop(session_id)
                if lst.get('stats_conn') and engine.state_manager.stats_manager:
                    try:
                        engine.state_manager.stats_manager.stats_changed.disconnect(lst['stats_conn'])
                    except Exception:
                        pass
                if lst.get('orch_conn'):
                    try:
                        engine.orchestrated_event_to_ui.disconnect(lst['orch_conn'])
                    except Exception:
                        pass
        except Exception:
            pass
        
        # Remove WebSocket connections
        if session_id in websocket_connections:
            for websocket in websocket_connections[session_id]:
                try:
                    await websocket.close()
                except:
                    pass
            del websocket_connections[session_id]
        
        logger.info(f"Ended session {session_id}")
        
        return {
            "status": "success",
            "message": f"Session {session_id} ended successfully"
        }
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ending session: {str(e)}"
        )

# Server startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize resources on server startup."""
    logger.info("API server starting up")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on server shutdown."""
    logger.info("API server shutting down")
    
    # Stop all game engines
    for session_id, engine in active_sessions.items():
        if engine.game_loop.is_running:
            engine.game_loop.stop()
    
    # Close all WebSocket connections
    for session_id, connections in websocket_connections.items():
        for websocket in connections:
            try:
                await websocket.close()
            except:
                pass

# LLM settings endpoints
@app.get("/api/llm/settings", response_model=LLMSettingsResponse)
async def get_llm_settings():
    """Get current LLM settings."""
    try:
        # Create settings manager
        settings_manager = SettingsManager()
        
        # Get provider settings
        provider_config = settings_manager.get_provider_settings()
        
        # Get agent settings
        agent_config = {
            "narrator": settings_manager.get_agent_settings("narrator"),
            "rule_checker": settings_manager.get_agent_settings("rule_checker"),
            "context_evaluator": settings_manager.get_agent_settings("context_evaluator")
        }
        
        # Get LLM enabled status from any active game engine or settings
        llm_enabled = False
        if active_sessions:
            # Use the first active engine to check if LLM is enabled
            engine = next(iter(active_sessions.values()))
            llm_enabled = engine._use_llm
        
        return {
            "providers": {
            "openai": {**provider_config.get("openai", {"api_key": "", "organization_id": "", "enabled": True})},
            "google": {**provider_config.get("google", {"api_key": "", "organization_id": "", "enabled": True})},
            "openrouter": {**provider_config.get("openrouter", {"api_key": "", "organization_id": "", "enabled": True})}
            },
            "agents": {
                "narrator": agent_config.get("narrator", {
                    "provider_type": "OPENAI",
                    "model": "gpt-4o", 
                    "temperature": 0.7,
                    "top_p": 1.0,
                    "max_tokens": 1000,
                    "enabled": True
                }),
                "rule_checker": agent_config.get("rule_checker", {
                    "provider_type": "GOOGLE",
                    "model": "gemini-2.0-flash", 
                    "temperature": 0.3,
                    "top_p": 1.0,
                    "max_tokens": 500,
                    "enabled": True
                }),
                "context_evaluator": agent_config.get("context_evaluator", {
                    "provider_type": "GOOGLE",
                    "model": "gemini-2.0-flash", 
                    "temperature": 0.2,
                    "top_p": 1.0,
                    "max_tokens": 800,
                    "enabled": True
                }),
            },
            "llm_enabled": llm_enabled,
        }
    except Exception as e:
        logger.error(f"Error getting LLM settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting LLM settings: {str(e)}"
        )

@app.post("/api/llm/settings")
async def update_llm_settings(providers: Optional[ProviderConfig] = None, agents: Optional[AgentConfig] = None):
    """Update LLM settings."""
    try:
        # Create settings manager
        settings_manager = SettingsManager()
        
        # Update provider settings
        if providers:
            for provider_name in ["openai", "google", "openrouter"]:
                if hasattr(providers, provider_name):
                    provider_settings = getattr(providers, provider_name)
                    if provider_settings:
                        settings_manager.update_provider_settings(
                            provider_name,
                            provider_settings.dict()
                        )
        
        # Update agent settings
        if agents:
            for agent_name in ["narrator", "rule_checker", "context_evaluator"]:
                if hasattr(agents, agent_name):
                    agent_settings = getattr(agents, agent_name)
                    if agent_settings:
                        settings_manager.update_agent_settings(
                            agent_name,
                            agent_settings.dict()
                        )
        
        # Apply settings to any active game engines
        for engine in active_sessions.values():
            # Re-initialize agent manager if needed
            if hasattr(engine, '_agent_manager') and engine._agent_manager is not None:
                engine._agent_manager.reload_settings()
        
        return {
            "status": "success",
            "message": "LLM settings updated"
        }
    except Exception as e:
        logger.error(f"Error updating LLM settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating LLM settings: {str(e)}"
        )

@app.post("/api/llm/toggle/{session_id}")
async def toggle_llm(session_id: str, request: ToggleLLMRequest, engine: GameEngine = Depends(get_game_engine)):
    """Toggle LLM functionality for a game session."""
    try:
        # Toggle LLM functionality
        engine.set_llm_enabled(request.enabled)
        
        return {
            "status": "success",
            "message": f"LLM functionality {'enabled' if request.enabled else 'disabled'}",
            "llm_enabled": request.enabled
        }
    except Exception as e:
        logger.error(f"Error toggling LLM: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling LLM: {str(e)}"
        )

@app.get("/api/ui/backgrounds")
async def list_ui_backgrounds():
    """List available GUI backgrounds (PNG/GIF) so the web UI can mirror Py GUI."""
    bg_dir = os.path.join(project_root, "images", "gui", "background")
    try:
        files = [f for f in os.listdir(bg_dir) if f.lower().endswith((".png", ".gif"))]
        files.sort()
    except Exception:
        files = []
    return {"backgrounds": files}

@app.get("/api/character-icons")
async def get_all_character_icons():
    """Get a list of all available character icons (flat list)."""
    try:
        icons = get_character_icons()
        return {"status": "success", "icons": icons}
    except Exception as e:
        logger.error(f"Error getting character icons: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting character icons: {str(e)}")

@app.get("/api/character-icons/filter")
async def get_filtered_character_icons(race: str = Query(...), path: str = Query(...), sex: str = Query("Other")):
    """Get a filtered list of character icons by race/class/sex subfolder and filename tags."""
    try:
        icons = get_character_icons_filtered(race, path, sex)
        return {"status": "success", "icons": icons}
    except Exception as e:
        logger.error(f"Error getting filtered icons: {e}")
        raise HTTPException(status_code=500, detail="Error getting filtered icons")

# --- Config endpoints ---
from core.base.config import get_config as _get_config_singleton

@app.get("/api/config/races")
async def api_config_races():
    try:
        cfg = _get_config_singleton()
        races = cfg.get_all("races") or {}
        names = sorted([data.get('name', rid) for rid, data in races.items()])
        return {"races": races, "names": names}
    except Exception as e:
        logger.error(f"Error reading races config: {e}")
        raise HTTPException(status_code=500, detail="Error reading races config")

@app.get("/api/config/classes")
async def api_config_classes():
    try:
        cfg = _get_config_singleton()
        classes = cfg.get_all("classes") or {}
        names = sorted([data.get('name', cid) for cid, data in classes.items()])
        return {"classes": classes, "names": names}
    except Exception as e:
        logger.error(f"Error reading classes config: {e}")
        raise HTTPException(status_code=500, detail="Error reading classes config")

@app.get("/api/config/origins")
async def api_config_origins():
    try:
        cfg = _get_config_singleton()
        origins = cfg.get_all("origins") or {}
        # Return as list for convenience + dict form
        origin_list = list(origins.values())
        origin_list.sort(key=lambda x: x.get('name', ''))
        return {"origins": origins, "list": origin_list}
    except Exception as e:
        logger.error(f"Error reading origins config: {e}")
        raise HTTPException(status_code=500, detail="Error reading origins config")

# --- Stats endpoints ---
@app.get("/api/stats/all/{session_id}")
async def api_stats_all(session_id: str, engine: GameEngine = Depends(get_game_engine)):
    try:
        sm = engine.state_manager.stats_manager
        if not sm:
            raise HTTPException(status_code=404, detail="Stats manager not available")
        return sm.get_all_stats()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all stats: {e}")
        raise HTTPException(status_code=500, detail="Error getting stats")

class StatModifiersQuery(BaseModel):
    stat: str

@app.get("/api/stats/modifiers/{session_id}")
async def api_stat_modifiers(session_id: str, stat: str = Query(...), engine: GameEngine = Depends(get_game_engine)):
    try:
        sm = engine.state_manager.stats_manager
        if not sm:
            raise HTTPException(status_code=404, detail="Stats manager not available")
        from core.stats.stats_base import StatType, DerivedStatType
        stat_key = stat.strip().upper()
        stat_enum = None
        try:
            stat_enum = StatType[stat_key]
        except KeyError:
            try:
                stat_enum = DerivedStatType[stat_key]
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Unknown stat '{stat}'")
        mods = sm.modifier_manager.get_modifiers_for_stat(stat_enum)
        # Convert modifiers to dicts if they have to_dict
        out = []
        for m in mods:
            try:
                out.append(m.to_dict())
            except Exception:
                # Basic projection
                out.append({
                    "id": getattr(m, 'id', None),
                    "source": getattr(m, 'source_name', ''),
                    "value": getattr(m, 'value', 0),
                    "is_percentage": getattr(m, 'is_percentage', False),
                    "duration": getattr(m, 'duration', None)
                })
        return {"stat": stat_key, "modifiers": out}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stat modifiers: {e}")
        raise HTTPException(status_code=500, detail="Error getting modifiers")

# --- Journal endpoints ---
class JournalCharacterUpdate(BaseModel):
    text: str

class JournalObjectiveStatus(BaseModel):
    quest_id: str
    objective_id: str
    completed: Optional[bool] = None
    failed: Optional[bool] = None

class JournalAbandonRequest(BaseModel):
    quest_id: str

class JournalNoteRequest(BaseModel):
    text: str

@app.get("/api/journal/{session_id}")
async def api_get_journal(session_id: str, engine: GameEngine = Depends(get_game_engine)):
    try:
        st = engine.state_manager.state
        return getattr(st, 'journal', {}) or {}
    except Exception as e:
        logger.error(f"Error getting journal: {e}")
        raise HTTPException(status_code=500, detail="Error getting journal")

@app.post("/api/journal/character/{session_id}")
async def api_update_journal_character(session_id: str, req: JournalCharacterUpdate, engine: GameEngine = Depends(get_game_engine)):
    try:
        st = engine.state_manager.state
        if not hasattr(st, 'journal') or st.journal is None:
            st.journal = {"character": "", "quests": {}, "notes": []}
        st.journal["character"] = req.text or ""
        # Broadcast simple journal update
        asyncio.create_task(ConnectionManager.send_update(session_id, {"type": "journal_updated", "data": st.journal}))
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating journal character: {e}")
        raise HTTPException(status_code=500, detail="Error updating journal character")

@app.post("/api/journal/objective_status/{session_id}")
async def api_update_objective_status(session_id: str, req: JournalObjectiveStatus, engine: GameEngine = Depends(get_game_engine)):
    try:
        st = engine.state_manager.state
        if not hasattr(st, 'journal') or st.journal is None:
            st.journal = {"character": "", "quests": {}, "notes": []}
        q = st.journal.setdefault("quests", {}).get(req.quest_id)
        if not q:
            raise HTTPException(status_code=404, detail="Quest not found")
        # Update objective
        for o in q.get("objectives", []):
            if o.get("id") == req.objective_id:
                if req.completed is not None:
                    o["completed"] = bool(req.completed)
                    if req.completed:
                        o["failed"] = False
                if req.failed is not None:
                    o["failed"] = bool(req.failed)
                    if req.failed:
                        o["completed"] = False
                break
        asyncio.create_task(ConnectionManager.send_update(session_id, {"type": "journal_updated", "data": st.journal}))
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating objective status: {e}")
        raise HTTPException(status_code=500, detail="Error updating objective status")

@app.post("/api/journal/abandon/{session_id}")
async def api_abandon_quest(session_id: str, req: JournalAbandonRequest, engine: GameEngine = Depends(get_game_engine)):
    try:
        st = engine.state_manager.state
        if not hasattr(st, 'journal') or st.journal is None:
            st.journal = {"character": "", "quests": {}, "notes": []}
        q = st.journal.setdefault("quests", {}).get(req.quest_id)
        if not q:
            raise HTTPException(status_code=404, detail="Quest not found")
        q["status"] = "failed"
        q["abandoned"] = True
        asyncio.create_task(ConnectionManager.send_update(session_id, {"type": "journal_updated", "data": st.journal}))
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error abandoning quest: {e}")
        raise HTTPException(status_code=500, detail="Error abandoning quest")

@app.post("/api/journal/add_note/{session_id}")
async def api_add_journal_note(session_id: str, req: JournalNoteRequest, engine: GameEngine = Depends(get_game_engine)):
    try:
        st = engine.state_manager.state
        if not hasattr(st, 'journal') or st.journal is None:
            st.journal = {"character": "", "quests": {}, "notes": []}
        notes = st.journal.setdefault("notes", [])
        note = {"id": str(uuid.uuid4()), "text": req.text or "", "created_at": datetime.now().isoformat()}
        notes.append(note)
        asyncio.create_task(ConnectionManager.send_update(session_id, {"type": "journal_updated", "data": st.journal}))
        return {"status": "success", "note": note}
    except Exception as e:
        logger.error(f"Error adding note: {e}")
        raise HTTPException(status_code=500, detail="Error adding note")

@app.delete("/api/journal/delete_note/{session_id}/{note_id}")
async def api_delete_journal_note(session_id: str, note_id: str, engine: GameEngine = Depends(get_game_engine)):
    try:
        st = engine.state_manager.state
        if not hasattr(st, 'journal') or st.journal is None:
            st.journal = {"character": "", "quests": {}, "notes": []}
        notes = st.journal.setdefault("notes", [])
        before = len(notes)
        notes[:] = [n for n in notes if str(n.get('id')) != str(note_id)]
        if len(notes) == before:
            raise HTTPException(status_code=404, detail="Note not found")
        asyncio.create_task(ConnectionManager.send_update(session_id, {"type": "journal_updated", "data": st.journal}))
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note: {e}")
        raise HTTPException(status_code=500, detail="Error deleting note")

# Run server directly with: uvicorn server:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
