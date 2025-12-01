#!/usr/bin/env python3
"""
Command line interface for managing LLM settings.

This module provides a command line utility for managing LLM settings,
including API keys, provider selection, and agent configuration.
"""

import argparse
import json
from typing import Dict, Any

from core.utils.logging_config import get_logger
from core.llm.settings_manager import get_settings_manager
from core.llm.provider_manager import ProviderType

# Get the module logger
logger = get_logger("LLM")

def print_header(text: str) -> None:
    """Print a header with decoration."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_section(text: str) -> None:
    """Print a section header."""
    print(f"\n-- {text} --")

def print_json(data: Dict[str, Any]) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2))

def format_provider_type(provider_type: ProviderType) -> str:
    """Format a provider type for display."""
    return provider_type.name.capitalize()

class SettingsCLI:
    """
    Command line interface for managing LLM settings.
    """
    
    def __init__(self):
        """Initialize the settings CLI."""
        self._settings_manager = get_settings_manager()
    
    def show_main_menu(self) -> None:
        """Show the main menu."""
        while True:
            print_header("LLM Settings Manager")
            print("\n1. Manage LLM General Settings")
            print("2. Manage Provider Settings")
            print("3. Manage Agent Settings")
            print("4. Run LLM Diagnostics")
            print("0. Exit")
            
            choice = input("\nEnter your choice: ")
            
            if choice == '1':
                self.manage_llm_settings()
            elif choice == '2':
                self.manage_provider_settings()
            elif choice == '3':
                self.manage_agent_settings()
            elif choice == '4':
                self.run_llm_diagnostics()
            elif choice == '0':
                print("Exiting. Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
    
    def manage_llm_settings(self) -> None:
        """Manage general LLM settings."""
        print_header("General LLM Settings")
        
        settings = self._settings_manager.get_llm_settings()
        print_json(settings)
        
        print_section("Update Settings")
        print("Which setting would you like to update? (Enter setting name, or 'back' to go back)")
        
        setting_name = input("> ")
        
        if setting_name.lower() == 'back':
            return
        
        if setting_name in settings:
            current_value = settings[setting_name]
            print(f"Current value: {current_value} (type: {type(current_value).__name__})")
            
            if isinstance(current_value, bool):
                new_value_str = input(f"New value (true/false): ").lower()
                new_value = new_value_str in ['true', 'yes', 'y', '1']
            elif isinstance(current_value, int):
                new_value = int(input(f"New value (integer): "))
            elif isinstance(current_value, float):
                new_value = float(input(f"New value (number): "))
            elif isinstance(current_value, list):
                print("Enter values separated by commas:")
                new_value = [item.strip() for item in input("> ").split(',')]
            elif isinstance(current_value, dict):
                print("Cannot update nested dictionary from CLI. Please edit the JSON file directly.")
                return
            else:
                new_value = input(f"New value (string): ")
            
            # Update the setting
            self._settings_manager.update_llm_settings({setting_name: new_value})
            print(f"Updated {setting_name} to {new_value}")
        else:
            print(f"Setting '{setting_name}' not found.")
    
    def manage_provider_settings(self) -> None:
        """Manage provider settings."""
        while True:
            print_header("Provider Settings")
            
            # Get provider settings
            all_settings = self._settings_manager.get_provider_settings()
            
            # Display provider menu
            for i, (provider, _) in enumerate(all_settings.items(), 1):
                print(f"{i}. {provider.capitalize()}")
            
            print("0. Back")
            
            choice = input("\nSelect provider: ")
            
            if choice == '0':
                return
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(all_settings):
                    provider = list(all_settings.keys())[index]
                    self.manage_specific_provider(provider)
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    def manage_specific_provider(self, provider_name: str) -> None:
        """
        Manage settings for a specific provider.
        
        Args:
            provider_name: The name of the provider.
        """
        provider_map = {
            "openai": ProviderType.OPENAI,
            "anthropic": ProviderType.ANTHROPIC,
            "google": ProviderType.GOOGLE,
            "openrouter": ProviderType.OPENROUTER
        }
        
        provider_type = provider_map.get(provider_name)
        if not provider_type:
            print(f"Unknown provider: {provider_name}")
            return
        
        while True:
            print_header(f"{provider_name.capitalize()} Provider Settings")
            
            # Get provider settings
            settings = self._settings_manager.get_provider_settings(provider_type)
            print_json(settings)
            
            print_section("Options")
            print("1. Update API Key")
            print("2. Toggle Provider Enabled")
            print("3. Change Default Model")
            print("0. Back")
            
            choice = input("\nEnter your choice: ")
            
            if choice == '1':
                api_key = input("Enter API Key (leave empty to cancel): ")
                if api_key:
                    self._settings_manager.set_api_key(provider_type, api_key)
                    print("API Key updated.")
            
            elif choice == '2':
                enabled = settings.get("enabled", False)
                new_enabled = not enabled
                self._settings_manager.enable_provider(provider_type, new_enabled)
                print(f"Provider {provider_name} {'enabled' if new_enabled else 'disabled'}.")
            
            elif choice == '3':
                # Get available models
                available_models = settings.get("available_models", [])
                
                print_section("Available Models")
                for i, model in enumerate(available_models, 1):
                    print(f"{i}. {model}")
                
                choice = input("\nSelect model (or enter a custom model name): ")
                
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(available_models):
                        model = available_models[index]
                    else:
                        raise ValueError
                except ValueError:
                    model = choice
                
                self._settings_manager.update_provider_settings(provider_type, {"default_model": model})
                print(f"Default model set to {model}.")
            
            elif choice == '0':
                return
            
            else:
                print("Invalid choice. Please try again.")
    
    def manage_agent_settings(self) -> None:
        """Manage agent settings."""
        while True:
            print_header("Agent Settings")
            
            # Get list of agents
            agents = self._settings_manager.list_available_agents()
            
            # Display agent menu
            for i, agent in enumerate(agents, 1):
                print(f"{i}. {agent.capitalize()}")
            
            print("0. Back")
            
            choice = input("\nSelect agent: ")
            
            if choice == '0':
                return
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(agents):
                    agent = agents[index]
                    self.manage_specific_agent(agent)
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    def manage_specific_agent(self, agent_name: str) -> None:
        """
        Manage settings for a specific agent.
        
        Args:
            agent_name: The name of the agent.
        """
        while True:
            print_header(f"{agent_name.capitalize()} Agent Settings")
            
            # Get agent settings
            settings = self._settings_manager.get_agent_settings(agent_name)
            print_json(settings)
            
            print_section("Options")
            print("1. Change Provider")
            print("2. Change Model")
            print("3. Update Temperature")
            print("4. Update Max Tokens")
            print("0. Back")
            
            choice = input("\nEnter your choice: ")
            
            if choice == '1':
                # Get available providers
                provider_types = [
                    ProviderType.OPENAI,
                    ProviderType.ANTHROPIC,
                    ProviderType.GOOGLE,
                    ProviderType.OPENROUTER
                ]
                
                print_section("Available Providers")
                for i, provider in enumerate(provider_types, 1):
                    print(f"{i}. {format_provider_type(provider)}")
                
                choice = input("\nSelect provider: ")
                
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(provider_types):
                        provider = provider_types[index]
                        self._settings_manager.set_agent_provider(agent_name, provider)
                        print(f"Provider set to {format_provider_type(provider)}.")
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a number.")
            
            elif choice == '2':
                # Get current provider
                provider_type = self._settings_manager.get_agent_provider(agent_name)
                
                if provider_type:
                    # Get available models for the provider
                    models = self._settings_manager.get_available_models(provider_type)
                    
                    print_section(f"Available Models for {format_provider_type(provider_type)}")
                    for i, model in enumerate(models, 1):
                        print(f"{i}. {model}")
                    
                    choice = input("\nSelect model (or enter a custom model name): ")
                    
                    try:
                        index = int(choice) - 1
                        if 0 <= index < len(models):
                            model = models[index]
                        else:
                            raise ValueError
                    except ValueError:
                        model = choice
                    
                    self._settings_manager.set_agent_model(agent_name, model)
                    print(f"Model set to {model}.")
                else:
                    print("Provider not set for this agent.")
            
            elif choice == '3':
                # Update temperature
                current_temp = settings.get("temperature", 0.7)
                print(f"Current temperature: {current_temp}")
                
                try:
                    new_temp = float(input("New temperature (0.0-1.0): "))
                    if 0.0 <= new_temp <= 1.0:
                        self._settings_manager.update_agent_settings(agent_name, {"temperature": new_temp})
                        print(f"Temperature set to {new_temp}.")
                    else:
                        print("Temperature must be between 0.0 and 1.0.")
                except ValueError:
                    print("Please enter a valid number.")
            
            elif choice == '4':
                # Update max tokens
                current_max = settings.get("max_tokens", 1000)
                print(f"Current max tokens: {current_max}")
                
                try:
                    new_max = int(input("New max tokens: "))
                    if new_max > 0:
                        self._settings_manager.update_agent_settings(agent_name, {"max_tokens": new_max})
                        print(f"Max tokens set to {new_max}.")
                    else:
                        print("Max tokens must be a positive number.")
                except ValueError:
                    print("Please enter a valid number.")
            
            elif choice == '0':
                return
            
            else:
                print("Invalid choice. Please try again.")
    
    def run_llm_diagnostics(self) -> None:
        """Run LLM diagnostics."""
        print_header("Running LLM Diagnostics")
        
        from core.llm.llm_manager import get_llm_manager
        
        llm_manager = get_llm_manager()
        diagnostics = llm_manager.run_llm_diagnostics()
        
        print_section("Diagnostic Results")
        print(f"Status: {diagnostics.get('status', 'unknown')}")
        print(f"Message: {diagnostics.get('message', 'No message')}")
        
        print_section("Provider Results")
        for provider, result in diagnostics.get("providers", {}).items():
            print(f"\n{provider}:")
            print(f"  Status: {result.get('status', 'unknown')}")
            
            if result.get("status") == "success":
                print(f"  Model: {result.get('model', 'unknown')}")
                print(f"  Response: {result.get('response_content', '')}")
                print(f"  Tokens: {result.get('tokens', {})}")
                print(f"  Cost: ${result.get('cost', 0):.6f}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="LLM Settings Manager CLI")
    
    parser.add_argument("--set-api-key", action="store_true", help="Set API key for a provider")
    parser.add_argument("--provider", type=str, help="Provider name (openai, anthropic, google, openrouter)")
    parser.add_argument("--key", type=str, help="API key")
    
    parser.add_argument("--enable", action="store_true", help="Enable a provider")
    parser.add_argument("--disable", action="store_true", help="Disable a provider")
    
    parser.add_argument("--list-providers", action="store_true", help="List available providers")
    parser.add_argument("--list-agents", action="store_true", help="List available agents")
    
    parser.add_argument("--show-diagnostics", action="store_true", help="Run LLM diagnostics")
    
    args = parser.parse_args()
    
    settings_manager = get_settings_manager()
    
    # Handle command line arguments
    if args.set_api_key:
        if not args.provider or not args.key:
            print("Error: --provider and --key required with --set-api-key")
            return
        
        provider_map = {
            "openai": ProviderType.OPENAI,
            "anthropic": ProviderType.ANTHROPIC,
            "google": ProviderType.GOOGLE,
            "openrouter": ProviderType.OPENROUTER
        }
        
        if args.provider.lower() not in provider_map:
            print(f"Error: Unknown provider '{args.provider}'. Must be one of: {', '.join(provider_map.keys())}")
            return
        
        provider_type = provider_map[args.provider.lower()]
        success = settings_manager.set_api_key(provider_type, args.key)
        
        if success:
            print(f"API key for {args.provider} updated successfully.")
        else:
            print(f"Failed to update API key for {args.provider}.")
    
    elif args.enable or args.disable:
        if not args.provider:
            print("Error: --provider required with --enable or --disable")
            return
        
        provider_map = {
            "openai": ProviderType.OPENAI,
            "anthropic": ProviderType.ANTHROPIC,
            "google": ProviderType.GOOGLE,
            "openrouter": ProviderType.OPENROUTER
        }
        
        if args.provider.lower() not in provider_map:
            print(f"Error: Unknown provider '{args.provider}'. Must be one of: {', '.join(provider_map.keys())}")
            return
        
        provider_type = provider_map[args.provider.lower()]
        success = settings_manager.enable_provider(provider_type, args.enable)
        
        if success:
            print(f"Provider {args.provider} {'enabled' if args.enable else 'disabled'} successfully.")
        else:
            print(f"Failed to {'enable' if args.enable else 'disable'} provider {args.provider}.")
    
    elif args.list_providers:
        provider_settings = settings_manager.get_provider_settings()
        print_header("Available Providers")
        
        for provider, settings in provider_settings.items():
            enabled = settings.get("enabled", False)
            api_key_set = bool(settings.get("api_key", ""))
            default_model = settings.get("default_model", "unknown")
            
            print(f"{provider.capitalize()}: {'Enabled' if enabled else 'Disabled'}, API Key: {'Set' if api_key_set else 'Not Set'}, Default Model: {default_model}")
    
    elif args.list_agents:
        agents = settings_manager.list_available_agents()
        print_header("Available Agents")
        
        for agent in agents:
            agent_settings = settings_manager.get_agent_settings(agent)
            provider_type_str = agent_settings.get("provider_type", "OPENAI")
            model = agent_settings.get("model", "default")
            
            print(f"{agent.capitalize()}: Provider={provider_type_str}, Model={model}")
    
    elif args.show_diagnostics:
        cli = SettingsCLI()
        cli.run_llm_diagnostics()
    
    else:
        # No arguments, run interactive CLI
        SettingsCLI().show_main_menu()


if __name__ == "__main__":
    main()