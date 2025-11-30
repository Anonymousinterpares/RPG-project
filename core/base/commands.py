#!/usr/bin/env python3
"""
Command processing for the RPG game.

This module provides a framework for registering, parsing, and executing
player commands. It includes a CommandProcessor class for handling commands
and a CommandResult dataclass for representing command execution results.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from enum import Enum, auto

from core.utils.logging_config import get_logger
from core.base.state import GameState

# Get the module logger
logger = get_logger("GAME")

class CommandStatus(Enum):
    """Status of a command execution."""
    SUCCESS = auto()
    FAILURE = auto()
    ERROR = auto()
    INVALID = auto()
    # Special statuses
    EXIT = auto()  # Command requests program exit
    HELP = auto()  # Command requests help


@dataclass
class CommandResult:
    """
    Result of a command execution.
    
    This dataclass contains information about the result of executing
    a command, including status, message, and any data produced.
    """
    status: CommandStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success(cls, message: str, data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """Create a success result."""
        return cls(CommandStatus.SUCCESS, message, data)
    
    @classmethod
    def failure(cls, message: str, data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """Create a failure result."""
        return cls(CommandStatus.FAILURE, message, data)
    
    @classmethod
    def error(cls, message: str, data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """Create an error result."""
        return cls(CommandStatus.ERROR, message, data)
    
    @classmethod
    def invalid(cls, message: str, data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """Create an invalid command result."""
        return cls(CommandStatus.INVALID, message, data)
    
    @classmethod
    def exit(cls, message: str = "Exiting the game.", data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """Create an exit result."""
        return cls(CommandStatus.EXIT, message, data)
    
    @classmethod
    def help(cls, message: str, data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """Create a help result."""
        return cls(CommandStatus.HELP, message, data)
    
    @property
    def is_success(self) -> bool:
        """Check if the result is a success."""
        return self.status == CommandStatus.SUCCESS
    
    @property
    def is_failure(self) -> bool:
        """Check if the result is a failure."""
        return self.status in [CommandStatus.FAILURE, CommandStatus.ERROR, CommandStatus.INVALID]
    
    @property
    def is_exit(self) -> bool:
        """Check if the result requests an exit."""
        return self.status == CommandStatus.EXIT
    
    @property
    def is_help(self) -> bool:
        """Check if the result requests help."""
        return self.status == CommandStatus.HELP


class CommandProcessor:
    """
    Processor for parsing and executing commands.
    
    This class manages the registration of command handlers and the
    processing of player input into commands. It handles both built-in
    commands and commands extracted from LLM responses.
    """
    
    # Singleton instance
    _instance = None
    
    # Command handler type
    CommandHandler = Callable[[GameState, List[str]], CommandResult]
    
    # Command help data
    @dataclass
    class CommandHelp:
        """Help information for a command."""
        command: str
        syntax: str
        description: str
        examples: List[str] = field(default_factory=list)
        aliases: List[str] = field(default_factory=list)
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(CommandProcessor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the command processor."""
        if self._initialized:
            return
        
        # Command handlers by name
        self._handlers: Dict[str, CommandProcessor.CommandHandler] = {}
        
        # Developer command handlers by name
        self._dev_handlers: Dict[str, CommandProcessor.CommandHandler] = {}
        
        # Command aliases (pointing to main command names)
        self._aliases: Dict[str, str] = {}
        
        # Help information by command name
        self._help_data: Dict[str, CommandProcessor.CommandHelp] = {}
        
        # LLM command extraction pattern
        self._llm_command_pattern = re.compile(r'\{([A-Z_]+)(?:\s+(.+?))?\}')
        
        # Register built-in meta commands (help, quit)
        self._register_meta_commands()
        
        self._initialized = True
    
    def _register_meta_commands(self):
        """Register meta commands like help and quit."""
        # Register the help command
        self.register_command(
            name="help",
            handler=self._help_command,
            syntax="help [command]",
            description="Display help information for commands.",
            examples=["help", "help save", "help inventory"],
            aliases=["?", "commands"]
        )
        
        # Register the quit command
        self.register_command(
            name="quit",
            handler=self._quit_command,
            syntax="quit",
            description="Exit the game.",
            examples=["quit"],
            aliases=["exit", "bye"]
        )
        
        # Register the save command
        self.register_command(
            name="save",
            handler=self._save_command,
            syntax="save [name]",
            description="Save the current game state.",
            examples=["save", "save my_adventure"],
            aliases=[]
        )
        
        # Register the load command
        self.register_command(
            name="load",
            handler=self._load_command,
            syntax="load <save_id_or_name>",
            description="Load a saved game state.",
            examples=["load 1", "load my_adventure"],
            aliases=[]
        )
        
        # Register the list_saves command
        self.register_command(
            name="list_saves",
            handler=self._list_saves_command,
            syntax="list_saves",
            description="List all available saved games.",
            examples=["list_saves"],
            aliases=["saves", "ls"]
        )
        
        # Register the look command
        self.register_command(
            name="look",
            handler=self._look_command,
            syntax="look [target]",
            description="Look around or examine something specific.",
            examples=["look", "look chest", "look north"],
            aliases=["examine", "inspect"]
        )
        
        # Register the llm command to toggle/check LLM status
        self.register_command(
            name="llm",
            handler=self._llm_command,
            syntax="llm [on|off|status]",
            description="Toggle or check the status of the LLM system.",
            examples=["llm on", "llm off", "llm status"],
            aliases=[]
        )
    
    def _help_command(self, game_state: GameState, args: List[str]) -> CommandResult:
        """
        Display help information for commands.
        
        Args:
            game_state: The current game state.
            args: Command arguments. Optional command name to get help for.
            
        Returns:
            CommandResult with help information.
        """
        # If a command was specified, check if it's a developer command
        if args and args[0]:
            command = args[0].lower()
            
            # Handle //help as a special case
            if command.startswith("//"):
                dev_command = command[2:]
                help_data = None
                
                # Check if it's in dev_handlers
                if dev_command in self._dev_handlers:
                    help_data = self.get_command_help(f"//dev:{dev_command}")
                
                if help_data:
                    # Build help text for specific command
                    help_text = [
                        f"Developer Command: {help_data.command}",
                        f"Syntax: {help_data.syntax}",
                        f"Description: {help_data.description[6:]}"  # Remove [DEV] prefix
                    ]
                    
                    if help_data.examples:
                        help_text.append("Examples:")
                        for example in help_data.examples:
                            help_text.append(f"  {example}")
                    
                    return CommandResult.success("\n".join(help_text))
                else:
                    return CommandResult.failure(f"No help available for developer command '{dev_command}'.")
            
            # If args[0] is "dev", show all developer commands
            if command == "dev":
                dev_commands = self.get_all_dev_commands()
                if not dev_commands:
                    return CommandResult.success("No developer commands are currently registered.")
                
                dev_commands.sort()  # Alphabetical order
                
                help_text = ["Available Developer Commands:"]
                
                for cmd in dev_commands:
                    help_data = self.get_command_help(f"//dev:{cmd}")
                    if help_data:
                        # Add a short description for each command
                        description = help_data.description.split('.')[0][6:] + '.'  # First sentence, remove [DEV] prefix
                        help_text.append(f"  //{cmd}: {description}")
                
                help_text.append("\nType '//<command>' to use a developer command.")
                help_text.append("Type 'help //command' for more information on a specific developer command.")
                
                return CommandResult.success("\n".join(help_text))
            
            # For regular commands
            help_data = self.get_command_help(command)
            
            if not help_data:
                return CommandResult.failure(f"No help available for '{command}'. Type 'help' for a list of commands.")
            
            # Build help text for specific command
            help_text = [
                f"Command: {help_data.command}",
                f"Syntax: {help_data.syntax}",
                f"Description: {help_data.description}"
            ]
            
            if help_data.aliases:
                help_text.append(f"Aliases: {', '.join(help_data.aliases)}")
            
            if help_data.examples:
                help_text.append("Examples:")
                for example in help_data.examples:
                    help_text.append(f"  {example}")
            
            return CommandResult.success("\n".join(help_text))
        
        # Otherwise, show a list of all commands
        commands = self.get_all_commands()
        commands.sort()  # Alphabetical order
        
        help_text = ["Available commands:"]
        
        for cmd in commands:
            help_data = self.get_command_help(cmd)
            if help_data:
                # Add a short description for each command
                description = help_data.description.split('.')[0] + '.'  # First sentence
                help_text.append(f"  {cmd}: {description}")
        
        help_text.append("\nType 'help <command>' for more information on a specific command.")
        
        # Add information about developer commands
        dev_commands = self.get_all_dev_commands()
        if dev_commands:
            help_text.append("\nDeveloper Commands:")
            help_text.append("Use '/help dev' to see available developer commands.")
        
        return CommandResult.success("\n".join(help_text))
    
    def _quit_command(self, game_state: GameState, args: List[str]) -> CommandResult:
        """
        Exit the game.
        
        Args:
            game_state: The current game state.
            args: Command arguments (ignored).
            
        Returns:
            CommandResult with EXIT status.
        """
        return CommandResult.exit("Exiting the game. Thank you for playing!")
    
    def _save_command(self, game_state: GameState, args: List[str]) -> CommandResult:
        """
        Save the current game state.
        
        Args:
            game_state: The current game state.
            args: Command arguments. Optional save name.
            
        Returns:
            CommandResult indicating success or failure.
        """
        import uuid
        from core.utils.save_manager import SaveManager
        
        # Get save name if provided
        save_name = args[0] if args else f"Save_{game_state.player.name}_{game_state.game_time.get_formatted_time()}"
        
        try:
            # Generate a unique ID for the save
            save_id = str(uuid.uuid4())
            
            # Create the save using the StateManager
            game_state.state_manager.save_game(save_id)
            
            # Update metadata with the SaveManager
            save_manager = SaveManager()
            save_manager.update_metadata(
                save_id=save_id,
                updates={
                    "save_name": save_name,
                    "player_name": game_state.player.name,
                    "player_level": game_state.player.level,
                    "world_time": game_state.game_time.get_formatted_time(),
                    "location": game_state.world.current_location,
                    "playtime": game_state.playtime
                }
            )
            
            return CommandResult.success(f"Game saved as '{save_name}'.")
        except Exception as e:
            logger.error(f"Error saving game: {e}", exc_info=True)
            return CommandResult.error(f"Failed to save game: {str(e)}")
    
    def _load_command(self, game_state: GameState, args: List[str]) -> CommandResult:
        """
        Load a saved game state.
        
        Args:
            game_state: The current game state.
            args: Command arguments. Required save ID or name.
            
        Returns:
            CommandResult indicating success or failure.
        """
        from core.utils.save_manager import SaveManager
        
        if not args:
            return CommandResult.invalid("Please specify a save ID or name to load.")
        
        save_id_or_name = args[0]
        save_manager = SaveManager()
        
        try:
            # First, try to interpret the argument as a save ID
            save_id = save_id_or_name
            
            # If it's not a UUID, try to find a save with the given name
            if not self._is_valid_uuid(save_id):
                # Get all saves and look for a name match
                saves = save_manager.get_save_list()
                for save in saves:
                    if save.save_name.lower() == save_id_or_name.lower():
                        save_id = save.save_id
                        break
                else:
                    return CommandResult.failure(f"No save found with ID or name '{save_id_or_name}'.")
            
            # Now load the game
            success = game_state.state_manager.load_game(save_id)
            
            if success:
                return CommandResult.success(f"Game loaded successfully.")
            else:
                return CommandResult.failure(f"Failed to load game with ID '{save_id}'.")
                
        except Exception as e:
            logger.error(f"Error loading game: {e}", exc_info=True)
            return CommandResult.error(f"Failed to load game: {str(e)}")
    
    def _look_command(self, game_state: GameState, args: List[str]) -> CommandResult:
        """
        Look around or examine something specific.
        
        Args:
            game_state: The current game state.
            args: Command arguments. Optional target to examine.
            
        Returns:
            CommandResult with description.
        """
        # Process the look command directly if LLM is disabled
        # Otherwise, it should be handled by the LLM
        from core.base.engine import get_game_engine
        engine = get_game_engine()
        
        # If LLM is enabled, this command should not be directly processed
        # The engine should route it to the LLM system
        if engine._use_llm:
            return CommandResult.success("This command should be processed by the LLM system. If you're seeing this message, there might be an issue with LLM integration.")
        
        # Basic fallback implementation for when LLM is disabled
        location = game_state.player.current_location
        target = " ".join(args) if args else None
        
        if not target:
            # Look around the current location
            return CommandResult.success(
                f"You are in {location}. This is a simple placeholder description since the LLM system is disabled."
                f"\nUse '/llm on' command to enable the LLM system for rich descriptions."
            )
        else:
            # Look at a specific target
            return CommandResult.success(
                f"You examine the {target}. This is a simple placeholder description since the LLM system is disabled."
                f"\nUse '/llm on' command to enable the LLM system for rich descriptions."
            )

    def _llm_command(self, game_state: GameState, args: List[str]) -> CommandResult:
        """
        Toggle or check the status of the LLM system.
        
        Args:
            game_state: The current game state.
            args: Command arguments. Optional subcommand (on, off, status).
            
        Returns:
            CommandResult indicating success or failure.
        """
        # Get the game engine (needed to toggle LLM)
        from core.base.engine import get_game_engine
        engine = get_game_engine()
        
        # Check if any arguments were provided
        if not args:
            # No arguments, just show status
            status = "enabled" if engine._use_llm else "disabled"
            return CommandResult.success(f"LLM system is currently {status}.")
        
        # Process the subcommand
        subcommand = args[0].lower()
        
        if subcommand == "on" or subcommand == "enable":
            engine.set_llm_enabled(True)
            return CommandResult.success("LLM system enabled.")
        
        elif subcommand == "off" or subcommand == "disable":
            engine.set_llm_enabled(False)
            return CommandResult.success("LLM system disabled.")
        
        elif subcommand == "status":
            status = "enabled" if engine._use_llm else "disabled"
            return CommandResult.success(f"LLM system is currently {status}.")
        
        else:
            return CommandResult.invalid(f"Unknown subcommand: {subcommand}. Use 'on', 'off', or 'status'.")
    
    def _list_saves_command(self, game_state: GameState, args: List[str]) -> CommandResult:
        """
        List all available saved games.
        
        Args:
            game_state: The current game state.
            args: Command arguments (ignored).
            
        Returns:
            CommandResult with list of saves.
        """
        from core.utils.save_manager import SaveManager
        
        try:
            save_manager = SaveManager()
            saves = save_manager.get_save_list()
            
            if not saves:
                return CommandResult.success("No saved games found.")
            
            result_lines = ["Available saved games:"]
            
            for i, save in enumerate(saves, 1):
                # Format: 1. Save Name (Player Name, Level X) - 2023-04-15 14:30
                result_lines.append(
                    f"{i}. {save.save_name} ({save.player_name}, Level {save.player_level}) - {save.formatted_save_time}"
                )
            
            result_lines.append("\nUse 'load <save_name>' to load a saved game.")
            
            return CommandResult.success("\n".join(result_lines))
        except Exception as e:
            logger.error(f"Error listing saves: {e}", exc_info=True)
            return CommandResult.error(f"Failed to list saves: {str(e)}")
    
    def _is_valid_uuid(self, uuid_str: str) -> bool:
        """Check if a string is a valid UUID."""
        try:
            import uuid
            uuid.UUID(uuid_str)
            return True
        except (ValueError, AttributeError):
            return False
    
    def register_command(self, 
                         name: str, 
                         handler: CommandHandler,
                         syntax: str = "",
                         description: str = "",
                         examples: List[str] = None,
                         aliases: List[str] = None) -> None:
        """
        Register a command handler.
        
        Args:
            name: The name of the command.
            handler: The function to handle the command.
            syntax: The command syntax.
            description: A description of the command.
            examples: Example usages of the command.
            aliases: Alternative names for the command.
        """
        # Register the handler
        self._handlers[name.lower()] = handler
        
        # Register help information
        self._help_data[name.lower()] = CommandProcessor.CommandHelp(
            command=name.lower(),
            syntax=syntax or f"{name} [args...]",
            description=description or "No description available.",
            examples=examples or [],
            aliases=aliases or []
        )
        
        # Register aliases
        if aliases:
            for alias in aliases:
                self._aliases[alias.lower()] = name.lower()
        
        logger.debug(f"Registered command: {name}")
        
    def register_dev_command(self, 
                           name: str, 
                           handler: CommandHandler,
                           syntax: str = "",
                           description: str = "",
                           examples: List[str] = None) -> None:
        """
        Register a developer command handler.
        
        Args:
            name: The name of the command (without // prefix).
            handler: The function to handle the command.
            syntax: The command syntax.
            description: A description of the command.
            examples: Example usages of the command.
        """
        if examples is None:
            examples = []
            
        # Add the handler to dev_handlers
        self._dev_handlers[name.lower()] = handler
        
        # Add help information (reusing the same help system)
        self._help_data[f"//dev:{name.lower()}"] = CommandProcessor.CommandHelp(
            command=f"//{name.lower()}",
            syntax=syntax or f"//{name} [args...]",
            description=f"[DEV] {description or 'No description available.'}",
            examples=[f"//{ex}" for ex in examples] if examples else [],
            aliases=[]
        )
        
        logger.debug(f"Registered developer command: //{name}")
    
    def get_command_handler(self, command: str) -> Optional[CommandHandler]:
        """
        Get the handler for a command.
        
        Args:
            command: The command name.
        
        Returns:
            The command handler, or None if not found.
        """
        command = command.lower()
        
        # Check for direct command
        if command in self._handlers:
            return self._handlers[command]
        
        # Check for alias
        if command in self._aliases:
            return self._handlers[self._aliases[command]]
        
        return None
    
    def get_all_commands(self) -> List[str]:
        """
        Get a list of all registered commands.
        
        Returns:
            A list of command names.
        """
        return list(self._handlers.keys())
        
    def get_all_dev_commands(self) -> List[str]:
        """
        Get a list of all registered developer commands.
        
        Returns:
            A list of command names.
        """
        return list(self._dev_handlers.keys())
    
    def get_command_help(self, command: str) -> Optional[CommandHelp]:
        """
        Get help information for a command.
        
        Args:
            command: The command name.
        
        Returns:
            The command help, or None if not found.
        """
        command = command.lower()
        
        # Check for direct command
        if command in self._help_data:
            return self._help_data[command]
        
        # Check for alias
        if command in self._aliases:
            return self._help_data[self._aliases[command]]
        
        return None
    
    def process_command(self, game_state: GameState, command_text: str) -> CommandResult:
        """
        Process a command.
        
        Args:
            game_state: The current game state.
            command_text: The command text to process.
        
        Returns:
            The result of executing the command.
        """
        if not command_text:
            return CommandResult.invalid("Please enter a command.")
        
        # Update last command in game state
        game_state.last_command = command_text
        
        # Check if it's a developer command (starts with //)
        if command_text.startswith("//"):
            # Extract the command name (without //)
            parts = command_text[2:].split(maxsplit=1)
            command_name = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            # Get the developer command handler
            handler = self._dev_handlers.get(command_name)
            if handler is None:
                return CommandResult.invalid(f"Unknown developer command: {command_name}")
            
            # Gate all developer commands behind QSettings dev/enabled
            try:
                from PySide6.QtCore import QSettings
                dev_enabled = bool(QSettings("RPGGame", "Settings").value("dev/enabled", False, type=bool))
            except Exception:
                dev_enabled = False
            if not dev_enabled:
                return CommandResult.failure("Developer Mode is disabled. Enable it in Settings to use developer commands.")
            
            try:
                # Execute the command
                logger.debug(f"Executing developer command: {command_name} with args: {args}")
                
                # Parse args
                arg_list = []
                if args:
                    # This regex splits by spaces except within quoted strings
                    arg_pattern = re.compile(r'(?:[^\s,"]|"(?:\\.|[^"])*")++') 
                    arg_list = arg_pattern.findall(args)
                    
                    # Remove quotes from quoted arguments
                    arg_list = [
                        arg[1:-1] if (arg.startswith('"') and arg.endswith('"')) else arg 
                        for arg in arg_list
                    ]
                
                # Call the handler
                result = handler(game_state, arg_list)
                
                # Log the result
                if result.is_success:
                    logger.debug(f"Developer command {command_name} succeeded: {result.message}")
                else:
                    logger.debug(f"Developer command {command_name} failed: {result.message}")
                
                return result
            except Exception as e:
                logger.error(f"Error executing developer command {command_name}: {e}", exc_info=True)
                return CommandResult.error(f"Error executing developer command: {e}")
        
        # Add to conversation history (if not a system command) - moved here after developer command check
        if not command_text.startswith("/"):
            game_state.add_conversation_entry("player", command_text)
            
            # In a full implementation, this would be sent to an LLM agent for natural
            # language processing. For now, we'll just treat it as a direct command.
            # We'll still parse as a command for the basic framework.
        
        # Parse the command (strip leading / if present)
        command_text = command_text.lstrip("/")
        parts = command_text.split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Get the command handler
        handler = self.get_command_handler(command_name)
        if handler is None:
            return CommandResult.invalid(f"Unknown command: {command_name}")
        
        try:
            # Execute the command
            logger.debug(f"Executing command: {command_name} with args: {args}")
            
            # Split args by whitespace, but respect quoted strings
            arg_list = []
            if args:
                # This regex splits by spaces except within quoted strings
                arg_pattern = re.compile(r'(?:[^\s,"]|"(?:\\.|[^"])*")++') 
                arg_list = arg_pattern.findall(args)
                
                # Remove quotes from quoted arguments
                arg_list = [
                    arg[1:-1] if (arg.startswith('"') and arg.endswith('"')) else arg 
                    for arg in arg_list
                ]
            
            # Call the handler
            result = handler(game_state, arg_list)
            
            # Log the result
            if result.is_success:
                logger.debug(f"Command {command_name} succeeded: {result.message}")
            else:
                logger.debug(f"Command {command_name} failed: {result.message}")
            
            return result
        except Exception as e:
            logger.error(f"Error executing command {command_name}: {e}", exc_info=True)
            return CommandResult.error(f"Error executing command: {e}")
    
    def extract_llm_commands(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract LLM commands from text.
        
        Args:
            text: The text to extract commands from.
        
        Returns:
            A list of (command, args) tuples.
        """
        matches = self._llm_command_pattern.findall(text)
        return [(command, args or "") for command, args in matches]
    
    def process_llm_commands(self, game_state: GameState, text: str) -> Tuple[str, List[CommandResult]]:
        """
        Process LLM commands embedded in text.
        
        Args:
            game_state: The current game state.
            text: The text containing LLM commands.
        
        Returns:
            A tuple of (processed_text, command_results).
        """
        # Extract commands
        commands = self.extract_llm_commands(text)
        
        # Store results
        results = []
        
        # Process each command and replace in the text
        processed_text = text
        
        for cmd, args in commands:
            # Check if command is registered
            handler = self.get_command_handler(cmd)
            
            if handler:
                # Split args
                arg_list = args.split() if args else []
                
                # Execute the command
                try:
                    result = handler(game_state, arg_list)
                    results.append(result)
                    
                    # Replace the command in the text with its result
                    pattern = rf'\{{{cmd}(?:\s+{re.escape(args)})?\}}'
                    replacement = result.message if result.is_success else f"[Command Error: {result.message}]"
                    processed_text = re.sub(pattern, replacement, processed_text)
                except Exception as e:
                    logger.error(f"Error executing LLM command {cmd}: {e}", exc_info=True)
                    pattern = rf'\{{{cmd}(?:\s+{re.escape(args)})?\}}'
                    processed_text = re.sub(pattern, f"[Command Error: {e}]", processed_text)
            else:
                # Unknown command
                logger.warning(f"Unknown LLM command: {cmd}")
                pattern = rf'\{{{cmd}(?:\s+{re.escape(args)})?\}}'
                processed_text = re.sub(pattern, f"[Unknown Command: {cmd}]", processed_text)
        
        return processed_text, results


# Convenience function
def get_command_processor() -> CommandProcessor:
    """Get the command processor instance."""
    return CommandProcessor()


# Example usage (this would be filled in during the Command Handlers phase)
if __name__ == "__main__":
    # Set up basic logging
    get_logger.basicConfig(level=get_logger.DEBUG)
    
    # Get the command processor - commands are now registered automatically
    processor = get_command_processor()
    
    print("Command registration example")
    print("Commands:", processor.get_all_commands())
    
    # Example of command processing
    from core.base.state import GameState, PlayerState, WorldState
    game_state = GameState(player=PlayerState(name="Test Player"))
    
    result = processor.process_command(game_state, "help")
    print(f"Result: {result.message}")
    
    # Test a few basic commands
    print("\nTesting more commands:")
    commands = ["quit", "help save", "list_saves"]
    
    for cmd in commands:
        print(f"\nExecuting: {cmd}")
        result = processor.process_command(game_state, cmd)
        print(f"Status: {result.status}")
        print(f"Result: {result.message}")
    
    # Example of LLM command processing
    text = "You find a chest. {ITEM_CREATE chest common container}"
    processed_text, results = processor.process_llm_commands(game_state, text)
    print(f"\nProcessed text: {processed_text}")