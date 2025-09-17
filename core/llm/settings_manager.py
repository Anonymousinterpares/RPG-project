#!/usr/bin/env python3
"""
Settings manager for LLM and agent configuration.

This module provides a SettingsManager class that handles viewing and modifying
LLM settings, API keys, and agent configurations.
"""

import os
import json
from typing import Dict, List, Optional, Any, Union
import logging

from core.utils.logging_config import get_logger
from core.base.config import get_config
from core.llm.provider_manager import ProviderType, get_provider_manager

# Get the module logger
logger = get_logger("LLM")

class SettingsManager:
    """
    Manager for LLM and agent settings.
    
    This class provides methods for viewing and modifying settings related
    to LLM providers, API keys, and agent configurations.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the settings manager."""
        if self._initialized:
            return
        
        logger.info("Initializing SettingsManager")
        
        # Get configuration
        self._config = get_config()
        
        # Get provider manager
        self._provider_manager = get_provider_manager()
        
        # Set paths
        self._llm_config_path = os.path.join("config", "llm", "base_config.json")
        self._providers_path = os.path.join("config", "llm", "providers.json")
        self._agents_dir = os.path.join("config", "llm", "agents")
        
        # Ensure directories exist
        os.makedirs(self._agents_dir, exist_ok=True)
        
        self._initialized = True
        logger.info("SettingsManager initialized")
    
    def get_llm_settings(self) -> Dict[str, Any]:
        """
        Get general LLM settings.
        
        Returns:
            Dictionary of LLM settings.
        """
        try:
            if os.path.exists(self._llm_config_path):
                with open(self._llm_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"LLM config file not found: {self._llm_config_path}")
                return {}
        except Exception as e:
            logger.error(f"Error getting LLM settings: {e}")
            return {}
    
    def update_llm_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Update general LLM settings.
        
        Args:
            settings: Dictionary of settings to update.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get current settings
            current_settings = self.get_llm_settings()
            
            # Update settings
            current_settings.update(settings)
            
            # Write updated settings
            with open(self._llm_config_path, 'w', encoding='utf-8') as f:
                json.dump(current_settings, f, indent=4)
            
            logger.info("Updated LLM settings")
            return True
        except Exception as e:
            logger.error(f"Error updating LLM settings: {e}")
            return False
    
    def get_provider_settings(self, provider_type: Optional[ProviderType] = None) -> Dict[str, Any]:
        """
        Get provider settings.
        
        Args:
            provider_type: The provider type. If None, get all provider settings.
        
        Returns:
            Dictionary of provider settings.
        """
        try:
            if os.path.exists(self._providers_path):
                with open(self._providers_path, 'r', encoding='utf-8') as f:
                    providers_data = json.load(f)
                
                if provider_type:
                    # Convert ProviderType to provider name
                    provider_map = {
                        ProviderType.OPENAI: "openai",
                        ProviderType.ANTHROPIC: "anthropic",
                        ProviderType.GOOGLE: "google",
                        ProviderType.OPENROUTER: "openrouter"
                    }
                    
                    provider_name = provider_map.get(provider_type)
                    if provider_name and provider_name in providers_data:
                        return providers_data[provider_name]
                    else:
                        logger.warning(f"Provider not found: {provider_type.name if provider_type else None}")
                        return {}
                else:
                    return providers_data
            else:
                logger.warning(f"Providers file not found: {self._providers_path}")
                return {}
        except Exception as e:
            logger.error(f"Error getting provider settings: {e}")
            return {}
    
    def update_provider_settings(self, provider_type: ProviderType, settings: Dict[str, Any]) -> bool:
        """
        Update settings for a provider.
        
        Args:
            provider_type: The type of provider.
            settings: The new settings.
        
        Returns:
            True if successful, False otherwise.
        """
        # Get provider name
        provider_map = {
            ProviderType.OPENAI: "openai",
            ProviderType.ANTHROPIC: "anthropic",
            ProviderType.GOOGLE: "google",
            ProviderType.OPENROUTER: "openrouter"
        }
        
        provider_name = provider_map.get(provider_type)
        if not provider_name:
            logger.error(f"Invalid provider type: {provider_type}")
            return False
        
        try:
            # Get all provider settings
            all_providers = self.get_provider_settings()
            
            # Update provider settings
            if provider_name in all_providers:
                all_providers[provider_name].update(settings)
            else:
                all_providers[provider_name] = settings
            
            # Write updated settings
            with open(self._providers_path, 'w', encoding='utf-8') as f:
                json.dump(all_providers, f, indent=4)
            
            # Update provider in provider manager
            self._provider_manager.update_provider_settings(provider_type, settings)
            
            logger.info(f"Updated settings for provider: {provider_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating provider settings: {e}")
            return False
    
    def set_api_key(self, provider_type: ProviderType, api_key: str) -> bool:
        """
        Set the API key for a provider.
        
        Args:
            provider_type: The type of provider.
            api_key: The API key.
        
        Returns:
            True if successful, False otherwise.
        """
        # Update provider settings with the new API key
        return self.update_provider_settings(provider_type, {"api_key": api_key})
    
    def get_agent_settings(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get agent settings.
        
        Args:
            agent_name: The name of the agent. If None, get all agent settings.
        
        Returns:
            Dictionary of agent settings.
        """
        if agent_name:
            # Get settings for a specific agent
            agent_path = os.path.join(self._agents_dir, f"{agent_name.lower()}.json")
            
            try:
                if os.path.exists(agent_path):
                    with open(agent_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    logger.warning(f"Agent settings file not found: {agent_path}")
                    return {}
            except Exception as e:
                logger.error(f"Error getting agent settings: {e}")
                return {}
        else:
            # Get settings for all agents
            agent_settings = {}
            
            try:
                for filename in os.listdir(self._agents_dir):
                    if filename.endswith(".json"):
                        agent_name = os.path.splitext(filename)[0]
                        agent_path = os.path.join(self._agents_dir, filename)
                        
                        with open(agent_path, 'r', encoding='utf-8') as f:
                            agent_settings[agent_name] = json.load(f)
            except Exception as e:
                logger.error(f"Error getting all agent settings: {e}")
            
            return agent_settings
    
    def update_agent_settings(self, agent_name: str, settings: Dict[str, Any]) -> bool:
        """
        Update settings for an agent.
        
        Args:
            agent_name: The name of the agent.
            settings: The new settings.
        
        Returns:
            True if successful, False otherwise.
        """
        agent_path = os.path.join(self._agents_dir, f"{agent_name.lower()}.json")
        
        try:
            # Get current settings
            current_settings = {}
            if os.path.exists(agent_path):
                with open(agent_path, 'r', encoding='utf-8') as f:
                    current_settings = json.load(f)
            
            # Update settings
            current_settings.update(settings)
            
            # Write updated settings
            with open(agent_path, 'w', encoding='utf-8') as f:
                json.dump(current_settings, f, indent=4)
            
            logger.info(f"Updated settings for agent: {agent_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating agent settings: {e}")
            return False
    
    def list_available_agents(self) -> List[str]:
        """
        List all available agents.
        
        Returns:
            List of agent names.
        """
        agents = []
        
        try:
            for filename in os.listdir(self._agents_dir):
                if filename.endswith(".json"):
                    agent_name = os.path.splitext(filename)[0]
                    agents.append(agent_name)
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
        
        return agents
    
    def get_agent_provider(self, agent_name: str) -> Optional[ProviderType]:
        """
        Get the provider type for an agent.
        
        Args:
            agent_name: The name of the agent.
        
        Returns:
            The provider type, or None if not found.
        """
        agent_settings = self.get_agent_settings(agent_name)
        
        if not agent_settings:
            return None
        
        provider_type_str = agent_settings.get("provider_type")
        
        if not provider_type_str:
            return None
        
        try:
            return ProviderType[provider_type_str]
        except (KeyError, ValueError):
            logger.warning(f"Invalid provider type in agent settings: {provider_type_str}")
            return None
    
    def set_agent_provider(self, agent_name: str, provider_type: ProviderType) -> bool:
        """
        Set the provider type for an agent.
        
        Args:
            agent_name: The name of the agent.
            provider_type: The provider type.
        
        Returns:
            True if successful, False otherwise.
        """
        return self.update_agent_settings(agent_name, {"provider_type": provider_type.name})
    
    def set_agent_model(self, agent_name: str, model: str) -> bool:
        """
        Set the model for an agent.
        
        Args:
            agent_name: The name of the agent.
            model: The model name.
        
        Returns:
            True if successful, False otherwise.
        """
        return self.update_agent_settings(agent_name, {"model": model})
    
    def get_available_models(self, provider_type: ProviderType) -> List[str]:
        """
        Get available models for a provider.
        
        Args:
            provider_type: The provider type.
        
        Returns:
            List of model names.
        """
        provider_settings = self.get_provider_settings(provider_type)
        return provider_settings.get("available_models", [])
    
    def is_provider_enabled(self, provider_type: ProviderType) -> bool:
        """
        Check if a provider is enabled.
        
        Args:
            provider_type: The provider type.
        
        Returns:
            True if enabled, False otherwise.
        """
        provider_settings = self.get_provider_settings(provider_type)
        return provider_settings.get("enabled", False)
    
    def enable_provider(self, provider_type: ProviderType, enabled: bool) -> bool:
        """
        Enable or disable a provider.
        
        Args:
            provider_type: The provider type.
            enabled: Whether to enable the provider.
        
        Returns:
            True if successful, False otherwise.
        """
        return self.update_provider_settings(provider_type, {"enabled": enabled})


# Convenience function
def get_settings_manager() -> SettingsManager:
    """Get the settings manager instance."""
    return SettingsManager()


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Create the settings manager
    manager = get_settings_manager()
    
    # Print LLM settings
    llm_settings = manager.get_llm_settings()
    print(f"LLM settings: {llm_settings}")
    
    # Print provider settings
    provider_settings = manager.get_provider_settings()
    print(f"Provider settings: {provider_settings}")
    
    # Print agent settings
    agent_settings = manager.get_agent_settings()
    print(f"Agent settings: {agent_settings}")