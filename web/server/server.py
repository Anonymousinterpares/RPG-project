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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Body
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
    """Scan for character icons in the images/character_icons directory."""
    # Set up the character icons directory path
    icons_dir = os.path.join(project_root, "images", "character_icons")
    
    # Create the directory if it doesn't exist
    os.makedirs(icons_dir, exist_ok=True)
    
    # List of supported image extensions
    supported_extensions = [".png", ".jpg", ".jpeg", ".gif"]
    
    # Scan for icon files
    icons = []
    for filename in os.listdir(icons_dir):
        # Check if the file has a supported extension
        if any(filename.lower().endswith(ext) for ext in supported_extensions):
            # Build the path and URL
            file_path = os.path.join(icons_dir, filename)
            # URL path used by the web client to access the icon
            url_path = f"/images/character_icons/{filename}"
            
            icons.append({
                "filename": filename,
                "path": file_path,
                "url": url_path
            })
    
    # Sort the icons by filename
    icons.sort(key=lambda x: x["filename"])
    
    return icons

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
    background: str = Field(default="Commoner", description="Background of the player character")
    sex: str = Field(default="Male", description="Sex/gender of the player character")
    character_image: Optional[str] = Field(None, description="Path to character portrait image")
    use_llm: bool = Field(default=True, description="Whether to enable LLM functionality for this game")
    
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
@app.post("/api/new_game", response_model=SessionInfo)
async def create_new_game(request: NewGameRequest):
    """Create a new game session."""
    try:
        session_id = str(uuid.uuid4())
        engine = GameEngine()
        
        # Initialize with the provided parameters
        engine.initialize(
            new_game=True, 
            player_name=request.player_name,
            race=request.race,
            path=request.path,
            background=request.background,
            sex=request.sex,
            character_image=request.character_image,
            use_llm=request.use_llm
        )
        
        # Log LLM status
        logger.info(f"LLM {'enabled' if engine._use_llm else 'disabled'} for new game session")
        
        # Store in active sessions
        active_sessions[session_id] = engine
        
        # Initialize WebSocket connections list
        websocket_connections[session_id] = []
        
        logger.info(f"Created new game session {session_id} for player {request.player_name}")
        
        # Get game state for more detailed response
        state = engine.state_manager.state
        
        # Prepare detailed response
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
        
        # Send update to WebSocket clients
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

@app.get("/api/character-icons")
async def get_all_character_icons():
    """Get a list of all available character icons."""
    try:
        icons = get_character_icons()
        return {
            "status": "success",
            "icons": icons
        }
    except Exception as e:
        logger.error(f"Error getting character icons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting character icons: {str(e)}"
        )

# Run server directly with: uvicorn server:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
