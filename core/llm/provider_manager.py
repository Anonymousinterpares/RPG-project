#!/usr/bin/env python3
"""
Provider manager for LLM interactions.

This module provides a ProviderManager class that handles initialization
and management of different LLM providers (OpenAI, Anthropic, Google).
"""

import os
import json
from typing import Dict, List, Optional, Any
from enum import Enum, auto
import threading

from core.utils.logging_config import get_logger
from core.base.config import get_config


# Load environment variables from .env if present (applies to GUI and web server contexts)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    # dotenv is optional; continue without failing if not available
    pass

# Import LLM provider libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Get the module logger
logger = get_logger("LLM")

class ProviderType(Enum):
    """Enum for different LLM providers."""
    OPENAI = auto()
    ANTHROPIC = auto()
    GOOGLE = auto()
    OPENROUTER = auto()

class ProviderManager:
    """
    Manager for LLM providers.
    
    This class handles initialization and management of different LLM providers,
    including API keys, client creation, and provider configuration.
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProviderManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the provider manager."""
        if self._initialized:
            return
        
        logger.info("Initializing ProviderManager")
        
        # Get configuration
        self._config = get_config()
        
        # Load provider settings
        self._provider_settings = self._load_provider_settings()
        
        # Initialize clients dictionary
        self._clients = {}
        
        # Initialize provider availability
        self._provider_availability = {
            ProviderType.OPENAI: OPENAI_AVAILABLE,
            ProviderType.ANTHROPIC: ANTHROPIC_AVAILABLE,
            ProviderType.GOOGLE: GOOGLE_AVAILABLE,
            ProviderType.OPENROUTER: OPENAI_AVAILABLE,  # OpenRouter uses OpenAI's API
        }
        
        # Initialization lock for thread safety
        self._init_lock = threading.Lock()
        
        # On-demand initialization; do not initialize all providers on startup
        # self._initialize_providers()
        
        self._initialized = True
        logger.info("ProviderManager initialized")

    def initialize_provider(self, provider_type: ProviderType) -> bool:
        """Initialize a specific LLM provider client."""
        with self._init_lock:
            if provider_type in self._clients:
                return True # Already initialized
            
            if provider_type == ProviderType.OPENAI:
                return self._initialize_openai()
            elif provider_type == ProviderType.ANTHROPIC:
                return self._initialize_anthropic()
            elif provider_type == ProviderType.GOOGLE:
                return self._initialize_google()
            elif provider_type == ProviderType.OPENROUTER:
                return self._initialize_openrouter()
        
        logger.warning(f"Attempted to initialize an unknown provider type: {provider_type.name}")
        return False

    def reload_settings(self):
        """Reload provider settings from the configuration file."""
        logger.info("Reloading ProviderManager settings...")
        self._provider_settings = self._load_provider_settings()
        # Clear all clients to force re-initialization with new settings
        self._clients = {}
        logger.info("ProviderManager settings reloaded and all clients cleared.")
    
    def _load_provider_settings(self) -> Dict[str, Any]:
        """
        Load provider settings from configuration files, then override with environment variables.
        
        Returns:
            Dictionary of provider settings.
        """
        # Default settings
        default_settings = {
            "openai": {
                "api_key": "",
                "organization": "",
                "api_base": "https://api.openai.com/v1",
                "default_model": "gpt-4o-mini",
                "available_models": ["gpt-4o-mini"],
                "enabled": True
            },

            "google": {
                "api_key": "",
                "default_model": "gemini-2.0-flash",
                "enabled": True
            },
            "openrouter": {
                "api_key": "",
                "api_base": "https://openrouter.ai/api/v1",
                "default_model": "nousresearch/deephermes-3-llama-3-8b-preview:free",
                "available_models": [
                "google/gemini-2.0-flash-exp:free",
                "google/gemini-2.0-flash-lite-preview-02-05:free",
                "nousresearch/deephermes-3-llama-3-8b-preview:free",
                "google/gemini-2.0-pro-exp-02-05:free",
                "mistralai/mistral-small-3.1-24b-instruct:free"
                ],
                "enabled": True
            }
        }
        
        # Try to load provider settings from file
        providers_file = os.path.join("config", "llm", "providers.json")
        if os.path.exists(providers_file):
            try:
                with open(providers_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    
                    # Merge with default settings
                    for provider, settings in loaded_settings.items():
                        if provider in default_settings:
                            default_settings[provider].update(settings)
                        else:
                            default_settings[provider] = settings
                            
                logger.info(f"Loaded provider settings from {providers_file}")
            except Exception as e:
                logger.error(f"Error loading provider settings: {e}")
        else:
            logger.warning(f"Provider settings file not found: {providers_file}")
            
            # Create default provider settings file
            try:
                os.makedirs(os.path.dirname(providers_file), exist_ok=True)
                with open(providers_file, 'w', encoding='utf-8') as f:
                    json.dump(default_settings, f, indent=4)
                logger.info(f"Created default provider settings file: {providers_file}")
            except Exception as e:
                logger.error(f"Error creating default provider settings file: {e}")
        
        # Override with environment variables if present (prefers env over file)
        env_overrides: Dict[str, Dict[str, Optional[str]]] = {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "organization": os.getenv("OPENAI_ORG") or os.getenv("OPENAI_ORGANIZATION"),
                "api_base": os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL"),
            },
            "google": {
                "api_key": os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            },
            "openrouter": {
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "api_base": os.getenv("OPENROUTER_API_BASE"),
            },
            "anthropic": {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
            },
        }
        
        for provider, fields in env_overrides.items():
            if provider not in default_settings:
                default_settings[provider] = {}
            for key, value in fields.items():
                if value and isinstance(value, str) and value.strip():
                    default_settings[provider][key] = value.strip()
                    # Don't log secrets; only note which provider field came from env
                    logger.debug(f"Using environment value for {provider}.{key}")
        
        return default_settings
    
    def _initialize_providers(self) -> None:
        """Initialize LLM provider clients."""
        self._initialize_openai()
        self._initialize_anthropic()
        self._initialize_google()
        self._initialize_openrouter()
    
    def _initialize_openai(self) -> bool:
        """Initialize OpenAI client."""
        if not self._provider_availability[ProviderType.OPENAI]:
            logger.warning("OpenAI library not available")
            return False
        
        settings = self._provider_settings.get("openai", {})
        if not settings.get("enabled", True):
            logger.info("OpenAI provider disabled in settings")
            return False
        
        api_key = settings.get("api_key", "")
        if not api_key:
            logger.warning("OpenAI API key not configured")
            return False
        
        try:
            # Initialize the client
            client = openai.OpenAI(
                api_key=api_key,
                organization=settings.get("organization", ""),
                base_url=settings.get("api_base", "https://api.openai.com/v1")
            )
            
            # Store the client
            self._clients[ProviderType.OPENAI] = {
                "client": client,
                "settings": settings
            }
            
            logger.info("OpenAI client initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            return False
    
    def _initialize_anthropic(self) -> bool:
        """Initialize Anthropic client."""
        if not self._provider_availability[ProviderType.ANTHROPIC]:
            logger.warning("Anthropic library not available")
            return False
        
        settings = self._provider_settings.get("anthropic", {})
        if not settings.get("enabled", True):
            logger.info("Anthropic provider disabled in settings")
            return False
        
        api_key = settings.get("api_key", "")
        if not api_key:
            logger.warning("Anthropic API key not configured")
            return False
        
        try:
            # Initialize the client
            client = anthropic.Anthropic(
                api_key=api_key
            )
            
            # Store the client
            self._clients[ProviderType.ANTHROPIC] = {
                "client": client,
                "settings": settings
            }
            
            logger.info("Anthropic client initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing Anthropic client: {e}")
            return False
    
    def _initialize_google(self) -> bool:
        """Initialize Google client."""
        if not self._provider_availability[ProviderType.GOOGLE]:
            logger.warning("Google library not available")
            return False
        
        settings = self._provider_settings.get("google", {})
        if not settings.get("enabled", True):
            logger.info("Google provider disabled in settings")
            return False
        
        api_key = settings.get("api_key", "")
        if not api_key:
            logger.warning("Google API key not configured")
            return False
        
        try:
            # Initialize the client
            genai.configure(api_key=api_key)
            
            # Store the client
            self._clients[ProviderType.GOOGLE] = {
                "client": genai,
                "settings": settings
            }
            
            logger.info("Google client initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing Google client: {e}")
            return False
    
    def _initialize_openrouter(self) -> bool:
        """Initialize OpenRouter client."""
        if not self._provider_availability[ProviderType.OPENROUTER]:
            logger.warning("OpenRouter requires OpenAI library which is not available")
            return False
        
        settings = self._provider_settings.get("openrouter", {})
        if not settings.get("enabled", True):
            logger.info("OpenRouter provider disabled in settings")
            return False
        
        api_key = settings.get("api_key", "")
        if not api_key:
            logger.warning("OpenRouter API key not configured")
            return False
        
        try:
            # Initialize the client
            client = openai.OpenAI(
                api_key=api_key,
                base_url=settings.get("api_base", "https://openrouter.ai/api/v1")
            )
            
            # Store the client
            self._clients[ProviderType.OPENROUTER] = {
                "client": client,
                "settings": settings
            }
            
            logger.info("OpenRouter client initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing OpenRouter client: {e}")
            return False
    
    def get_client(self, provider_type: ProviderType) -> Optional[Any]:
        """
        Get a provider client.
        
        Args:
            provider_type: The type of provider.
        
        Returns:
            The provider client, or None if not available.
        """
        if provider_type not in self._clients:
            return None
        
        return self._clients[provider_type]["client"]

    def clear_client(self, provider_type: ProviderType):
        """
        Clear a cached client, forcing re-initialization on next use.
        
        Args:
            provider_type: The type of provider client to clear.
        """
        if provider_type in self._clients:
            del self._clients[provider_type]
            logger.info(f"Cleared cached client for {provider_type.name}. It will be re-initialized on next use.")
    
    def get_provider_settings(self, provider_type: ProviderType) -> Dict[str, Any]:
        """
        Get provider settings.
        
        Args:
            provider_type: The type of provider.
        
        Returns:
            The provider settings.
        """
        provider_map = {
            ProviderType.OPENAI: "openai",
            ProviderType.ANTHROPIC: "anthropic",
            ProviderType.GOOGLE: "google",
            ProviderType.OPENROUTER: "openrouter"
        }
        
        provider_name = provider_map.get(provider_type)
        return self._provider_settings.get(provider_name, {})
    
    def is_provider_available(self, provider_type: ProviderType) -> bool:
        """
        Check if a provider is available for use (library installed, enabled, and configured).
        
        Args:
            provider_type: The type of provider.
        
        Returns:
            True if the provider is available, False otherwise.
        """
        # 1. Check library availability
        if not self._provider_availability.get(provider_type, False):
            return False
        
        # 2. Get provider settings
        provider_map = {
            ProviderType.OPENAI: "openai",
            ProviderType.ANTHROPIC: "anthropic",
            ProviderType.GOOGLE: "google",
            ProviderType.OPENROUTER: "openrouter"
        }
        provider_name = provider_map.get(provider_type)
        if not provider_name:
            return False
            
        settings = self._provider_settings.get(provider_name, {})
        
        # 3. Check if enabled in settings
        if not settings.get("enabled", True):
            return False
            
        # 4. Check for API key
        api_key = settings.get("api_key", "")
        if not api_key:
            return False
            
        return True
    
    def get_available_providers(self) -> List[ProviderType]:
        """
        Get a list of available providers.
        
        Returns:
            List of available provider types.
        """
        return [
            provider for provider in ProviderType 
            if self.is_provider_available(provider)
        ]
    
    def verify_client(self, provider_type: ProviderType) -> bool:
        """
        Verify that a provider client is working by initializing it if needed and making a test call.
        
        Args:
            provider_type: The type of provider to verify.
        
        Returns:
            True if the client is working, False otherwise.
        """
        # First, check if the provider is configured to be available (libs, settings, key)
        if not self.is_provider_available(provider_type):
            logger.warning(f"Cannot verify {provider_type.name}: provider is not available or configured.")
            return False
        
        # Attempt to initialize the provider
        if not self.initialize_provider(provider_type):
            logger.warning(f"Failed to initialize provider {provider_type.name} during verification.")
            return False

        # Get the client
        client = self.get_client(provider_type)
        if not client:
            logger.warning(f"Failed to get client for {provider_type.name} after initialization.")
            return False
        
        # Test prompt
        test_prompt = "Hello, this is a test prompt to verify API connectivity. Please respond with 'OK'."
        
        try:
            # Attempt to get a completion based on provider type
            if provider_type == ProviderType.OPENAI:
                response = client.chat.completions.create(
                    model=self.get_provider_settings(provider_type).get("default_model"),
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=10
                )
                return True
            
            elif provider_type == ProviderType.ANTHROPIC:
                response = client.completions.create(
                    prompt=f"\n\nHuman: {test_prompt}\n\nAssistant:",
                    model=self.get_provider_settings(provider_type).get("default_model"),
                    max_tokens_to_sample=10
                )
                return True
            
            elif provider_type == ProviderType.GOOGLE:
                model = client.GenerativeModel(
                    self.get_provider_settings(provider_type).get("default_model")
                )
                response = model.generate_content(test_prompt)
                return True
            
            elif provider_type == ProviderType.OPENROUTER:
                response = client.chat.completions.create(
                    model=self.get_provider_settings(provider_type).get("default_model"),
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=10
                )
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error verifying {provider_type.name} client: {e}")
            return False
    
    def get_default_provider(self) -> Optional[ProviderType]:
        """
        Get the default provider type based on availability.
        
        Returns:
            The default provider type, or None if no providers are available.
        """
        available_providers = self.get_available_providers()
        
        if not available_providers:
            return None
            
        # Return the first available provider in priority order
        priority_order = [
            ProviderType.OPENAI, 
            ProviderType.ANTHROPIC, 
            ProviderType.GOOGLE,
            ProviderType.OPENROUTER
        ]
        
        for provider in priority_order:
            if provider in available_providers:
                return provider
        
        # If none in priority order, return the first available
        return available_providers[0]
    
    def update_provider_settings(self, provider_type: ProviderType, 
                                settings: Dict[str, Any]) -> bool:
        """
        Update settings for a provider and clear the client to force re-initialization.
        
        Args:
            provider_type: The type of provider.
            settings: The new settings.
        
        Returns:
            True if the settings were updated successfully, False otherwise.
        """
        provider_map = {
            ProviderType.OPENAI: "openai",
            ProviderType.ANTHROPIC: "anthropic",
            ProviderType.GOOGLE: "google",
            ProviderType.OPENROUTER: "openrouter"
        }
        
        provider_name = provider_map.get(provider_type)
        if not provider_name:
            return False
        
        try:
            # Update in-memory settings
            if provider_name in self._provider_settings:
                self._provider_settings[provider_name].update(settings)
            else:
                self._provider_settings[provider_name] = settings
            
            # Update settings file
            providers_file = os.path.join("config", "llm", "providers.json")
            with open(providers_file, 'w', encoding='utf-8') as f:
                json.dump(self._provider_settings, f, indent=4)
            
            # Clear the client to force re-initialization with new settings on next use
            self.clear_client(provider_type)
            
            logger.info(f"Updated settings for provider: {provider_name}. Client will be re-initialized on next use.")
            return True
        
        except Exception as e:
            logger.error(f"Error updating provider settings: {e}")
            return False


# Convenience function
def get_provider_manager() -> ProviderManager:
    """Get the provider manager instance."""
    return ProviderManager()


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logger.basicConfig(level=logger.INFO)
    
    # Create the provider manager
    manager = get_provider_manager()
    
    # Check available providers
    available_providers = manager.get_available_providers()
    print(f"Available providers: {[p.name for p in available_providers]}")
    
    # Get default provider
    default_provider = manager.get_default_provider()
    if default_provider:
        print(f"Default provider: {default_provider.name}")
    else:
        print("No providers available")