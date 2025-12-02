#!/usr/bin/env python3
"""
LLM manager for handling completions and interactions.

This module provides a LLMManager class that handles high-level LLM
interactions, including prompt formatting, completion retrieval,
and error handling.
"""

import os
import time
import json
import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import threading

from core.utils.logging_config import get_logger
from core.base.config import get_config
from core.llm.provider_manager import ProviderManager, ProviderType, get_provider_manager

# Get the module logger
logger = get_logger("LLM")

class LLMRole(str, Enum):
    """Roles for LLM conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

class LLMResponse:
    """
    Response from an LLM.
    
    This class represents a response from an LLM, including
    the content, token usage, and provider information.
    """
    
    def __init__(self, 
                 content: str,
                 provider_type: ProviderType,
                 model: str,
                 prompt_tokens: int = 0,
                 completion_tokens: int = 0,
                 total_tokens: int = 0,
                 cost: float = 0.0,
                 finish_reason: Optional[str] = None):
        """Initialize the LLM response."""
        self.content = content
        self.provider_type = provider_type
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens or (prompt_tokens + completion_tokens)
        self.cost = cost
        self.finish_reason = finish_reason
        self.timestamp = datetime.datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "provider_type": self.provider_type.name,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "finish_reason": self.finish_reason,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMResponse':
        """Create an LLMResponse from a dictionary."""
        provider_type = ProviderType[data.get("provider_type", "OPENAI")]
        return cls(
            content=data.get("content", ""),
            provider_type=provider_type,
            model=data.get("model", "unknown"),
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            cost=data.get("cost", 0.0),
            finish_reason=data.get("finish_reason")
        )


class LLMManager:
    """
    Manager for LLM interactions.
    
    This class handles high-level LLM interactions, including
    prompt formatting, completion retrieval, and error handling.
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LLMManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the LLM manager."""
        if self._initialized:
            return
        
        logger.info("Initializing LLMManager")
        
        # Get configuration
        self._config = get_config()
        
        # Get provider manager
        self._provider_manager = get_provider_manager()
        
        # Load LLM settings
        self._llm_settings = self._load_llm_settings()
        
        # Proactively initialize configured providers
        self._initialize_configured_providers()

        # Previously: optionally run diagnostics on startup based on settings.
        # Now: diagnostics are initiated from the GUI/CLI on-demand. Startup should not test providers.
        self._run_diagnostics = self._llm_settings.get("run_diagnostics_on_start", False)
        logger.debug("Skipping LLM diagnostics on startup; will run on-demand from GUI/CLI if requested.")
        
        self._initialized = True
        logger.info("LLMManager initialized")
        
    def _initialize_configured_providers(self):
        """Scan configs and initialize all providers that are actually in use."""
        logger.info("Scanning configurations to initialize required LLM providers...")
        required_providers = set()

        # 1. Get the default provider
        default_provider_str = self._llm_settings.get("default_provider_type")
        if default_provider_str:
            try:
                required_providers.add(ProviderType[default_provider_str])
            except (KeyError, ValueError):
                logger.warning(f"Invalid default provider type '{default_provider_str}' in base config.")

        # 2. Scan all agent configurations
        agents_config_dir = os.path.join("config", "llm", "agents")
        if os.path.isdir(agents_config_dir):
            for filename in os.listdir(agents_config_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(agents_config_dir, filename), 'r', encoding='utf-8') as f:
                            agent_config = json.load(f)
                            agent_provider_str = agent_config.get("provider_type")
                            if agent_provider_str:
                                try:
                                    required_providers.add(ProviderType[agent_provider_str])
                                except (KeyError, ValueError):
                                    logger.warning(f"Invalid provider type '{agent_provider_str}' in agent config '{filename}'.")
                    except Exception as e:
                        logger.error(f"Error reading agent config file {filename}: {e}")

        # 3. Initialize the unique set of required providers
        if not required_providers:
            logger.warning("No providers found in configurations. LLM functionality may be limited.")
            return
            
        logger.info(f"Found {len(required_providers)} required providers: {[p.name for p in required_providers]}")
        for provider_type in required_providers:
            if self._provider_manager.is_provider_available(provider_type):
                self._provider_manager.initialize_provider(provider_type)
            else:
                logger.warning(f"Configured provider {provider_type.name} is not available (check library installation, settings, and API key).")
            
    def reload_settings(self):
        """Reload LLM and provider settings from configuration files."""
        logger.info("Reloading LLMManager settings...")
        self._llm_settings = self._load_llm_settings()
        self._provider_manager.reload_settings()
        # After reloading, re-initialize the configured providers
        self._initialize_configured_providers()
        logger.info("LLMManager settings reloaded.")   
         
    def _load_llm_settings(self) -> Dict[str, Any]:
        """
        Load LLM settings from configuration.
        
        Returns:
            Dictionary of LLM settings.
        """
        # Default settings
        default_settings = {
            "default_provider_type": "OPENAI",
            "default_temperature": 0.7,
            "max_tokens": 1000,
            "timeout_seconds": 30,
            "retry_attempts": 3,
            "retry_delay_seconds": 2,
            "run_diagnostics_on_start": False,
            "log_prompts": True,
            "log_completions": True,
            "cost_tracking_enabled": True
        }
        
        # Get settings from config
        config_settings = self._config.get("llm", {})
        
        # Merge with default settings
        merged_settings = {**default_settings, **config_settings}
        
        return merged_settings
    
    def get_completion(self, 
                      messages: List[Dict[str, str]],
                      provider_type: Optional[ProviderType] = None,
                      model: Optional[str] = None,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None,
                      timeout: Optional[int] = None,
                      retry_attempts: Optional[int] = None) -> Optional[LLMResponse]:
        """
        Get a completion from an LLM.
        
        Args:
            messages: List of message dictionaries (role, content).
            provider_type: The provider type to use. If None, uses the default.
            model: The model to use. If None, uses the provider's default.
            temperature: The temperature to use. If None, uses the default.
            max_tokens: The maximum number of tokens to generate. If None, uses the default.
            timeout: The timeout in seconds. If None, uses the default.
            retry_attempts: The number of retry attempts. If None, uses the default.
        
        Returns:
            An LLMResponse object, or None if the request failed.
        """
        # Determine the provider type
        if provider_type is None:
            provider_type_str = self._llm_settings.get("default_provider_type", "OPENAI")
            try:
                provider_type = ProviderType[provider_type_str]
            except (KeyError, ValueError):
                provider_type = ProviderType.OPENAI
                logger.warning(f"Invalid default provider type: {provider_type_str}. Using OpenAI.")
        
        # Check if the provider is available
        if not self._provider_manager.is_provider_available(provider_type):
            # Try to find an available provider
            fallback_provider = self._provider_manager.get_default_provider()
            if fallback_provider is None:
                logger.error("No LLM providers available")
                return None
            
            logger.warning(f"Provider {provider_type.name} not available. Falling back to {fallback_provider.name}.")
            provider_type = fallback_provider
        
        # Get provider client and settings
        client = self._provider_manager.get_client(provider_type)
        
        # Add a check to ensure the client was initialized successfully
        if client is None:
            logger.error(f"Failed to get a valid client for provider {provider_type.name}. Check API keys and settings.")
            return None
            
        provider_settings = self._provider_manager.get_provider_settings(provider_type)
        
        # Determine model
        if model is None:
            model = provider_settings.get("default_model")
        
        # Set parameters
        temperature = temperature if temperature is not None else self._llm_settings.get("default_temperature", 0.7)
        max_tokens = max_tokens if max_tokens is not None else self._llm_settings.get("max_tokens", 1000)

        # For OpenAI and OpenRouter 'gpt5' and 'gpt-5' models, override temperature to 1.0 (as other values are unsupported)
        if (provider_type == ProviderType.OPENAI or provider_type == ProviderType.OPENROUTER) and model and (model.startswith("gpt5") or model.startswith("gpt-5")):
            logger.debug(f"LLM Parameter: Overriding temperature for '{model}' to 1.0 (previously {temperature}) in get_completion.")
            temperature = 1.0
        timeout = timeout if timeout is not None else self._llm_settings.get("timeout_seconds", 30)
        retry_attempts = retry_attempts if retry_attempts is not None else self._llm_settings.get("retry_attempts", 3)
        
        # Log the request
        if self._llm_settings.get("log_prompts", True):
            logger.debug(f"LLM Request: provider={provider_type.name}, model={model}, temperature={temperature}")
            for msg in messages:
                logger.debug(f"  {msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}...")
        
        # Make the request with retries
        for attempt in range(retry_attempts + 1):
            try:
                if provider_type == ProviderType.OPENAI or provider_type == ProviderType.OPENROUTER:
                    return self._get_openai_completion(
                        client=client,
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                        provider_type=provider_type
                    )
                
                elif provider_type == ProviderType.ANTHROPIC:
                    return self._get_anthropic_completion(
                        client=client,
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                        provider_type=provider_type
                    )
                
                elif provider_type == ProviderType.GOOGLE:
                    return self._get_google_completion(
                        client=client,
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                        provider_type=provider_type
                    )
                
                else:
                    logger.error(f"Unsupported provider type: {provider_type.name}")
                    return None
                
            except Exception as e:
                if attempt < retry_attempts:
                    retry_delay = self._llm_settings.get("retry_delay_seconds", 2)
                    logger.warning(f"LLM request failed (attempt {attempt+1}/{retry_attempts+1}): {e}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"LLM request failed after {retry_attempts+1} attempts: {e}")
                    return None
    
    def _get_openai_completion(self,
                              client: Any,
                              messages: List[Dict[str, str]],
                              model: str,
                              temperature: float,
                              max_tokens: int,
                              timeout: int,
                              provider_type: ProviderType) -> Optional[LLMResponse]:
        """
        Get a completion from OpenAI.
        
        Args:
            client: The OpenAI client.
            messages: List of message dictionaries.
            model: The model to use.
            temperature: The temperature to use.
            max_tokens: The maximum number of tokens to generate.
            timeout: The timeout in seconds.
            provider_type: The provider type (OpenAI or OpenRouter).
        
        Returns:
            An LLMResponse object, or None if the request failed.
        """
        # Determine the correct token parameter name
        token_param_name = "max_tokens"
        if provider_type == ProviderType.OPENAI or provider_type == ProviderType.OPENROUTER:
            # Based on user feedback: gpt-4o (not gpt-4o-mini) and potentially gpt-5/gpt5 models require 'max_completion_tokens'
            if (model.startswith("gpt-4o") and not model.startswith("gpt-4o-mini")) or model.startswith("gpt-5") or model.startswith("gpt5"):
                token_param_name = "max_completion_tokens"
        
        logger.debug(f"LLM Parameter: Using '{token_param_name}' for model '{model}' with value {max_tokens}")

        # Create the request parameters
        # Create the request parameters
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature, # Ensure temperature is always passed here
            token_param_name: max_tokens,
            "timeout": timeout
        }
        
        # Make the request
        response = client.chat.completions.create(**request_params)
        
        # Parse the response
        try:
            # Check if response is None or doesn't have expected structure
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.error(f"Invalid response format from {provider_type.name}: {response}")
                return None

            # Get message content
            content = response.choices[0].message.content
            
            # Get token usage (with fallbacks for OpenRouter which may not provide usage)
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = getattr(response.usage, 'prompt_tokens', 0)
                completion_tokens = getattr(response.usage, 'completion_tokens', 0)
                total_tokens = getattr(response.usage, 'total_tokens', 0) or (prompt_tokens + completion_tokens)
            else:
                # Estimate tokens if usage not provided
                logger.warning(f"Token usage not provided by {provider_type.name}, estimating")
                prompt_tokens = sum(len(msg.get("content", "")) for msg in messages) // 4  # Rough estimate
                completion_tokens = len(content) // 4  # Rough estimate
                total_tokens = prompt_tokens + completion_tokens
            
            # Get finish reason (with fallback)
            finish_reason = getattr(response.choices[0], 'finish_reason', 'unknown')
            
            # Log completion
            if self._llm_settings.get("log_completions", True):
                logger.debug(f"LLM Completion: provider={provider_type.name}, model={model}, tokens={total_tokens}")
                logger.debug(f"  content: {content[:100]}...")
            
            # Calculate cost (this is an approximation)
            cost = self._calculate_cost(model, prompt_tokens, completion_tokens, provider_type)
            
            return LLMResponse(
                content=content,
                provider_type=provider_type,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                finish_reason=finish_reason
            )
            
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            return None
    
    def _get_anthropic_completion(self,
                                 client: Any,
                                 messages: List[Dict[str, str]],
                                 model: str,
                                 temperature: float,
                                 max_tokens: int,
                                 timeout: int,
                                 provider_type: ProviderType) -> Optional[LLMResponse]:
        """
        Get a completion from Anthropic.
        
        Args:
            client: The Anthropic client.
            messages: List of message dictionaries.
            model: The model to use.
            temperature: The temperature to use.
            max_tokens: The maximum number of tokens to generate.
            timeout: The timeout in seconds.
            provider_type: The provider type.
        
        Returns:
            An LLMResponse object, or None if the request failed.
        """
        # Convert messages to Anthropic format (human/assistant conversation)
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # Anthropic doesn't have system messages; add to the first user message
                continue
            elif role == "user":
                prompt += f"\n\nHuman: {content}"
            elif role == "assistant":
                prompt += f"\n\nAssistant: {content}"
        
        # Add final assistant prompt
        prompt += "\n\nAssistant:"
        
        # Create the request parameters
        request_params = {
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "max_tokens_to_sample": max_tokens,
            "stop_sequences": ["\n\nHuman:"]
        }
        
        # Make the request
        response = client.completions.create(**request_params)
        
        # Parse the response
        try:
            content = response.completion
            
            # Anthropic doesn't provide token usage in the response
            # We can estimate based on content length
            prompt_tokens = len(prompt) // 4  # Rough estimate
            completion_tokens = len(content) // 4  # Rough estimate
            total_tokens = prompt_tokens + completion_tokens
            
            # Log completion
            if self._llm_settings.get("log_completions", True):
                logger.debug(f"LLM Completion: provider={provider_type.name}, model={model}, est_tokens={total_tokens}")
                logger.debug(f"  content: {content[:100]}...")
            
            # Calculate cost (this is an approximation)
            cost = self._calculate_cost(model, prompt_tokens, completion_tokens, provider_type)
            
            return LLMResponse(
                content=content,
                provider_type=provider_type,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                finish_reason="stop"
            )
            
        except Exception as e:
            logger.error(f"Error parsing Anthropic response: {e}")
            return None
    
    def _get_google_completion(self,
                              client: Any,
                              messages: List[Dict[str, str]],
                              model: str,
                              temperature: float,
                              max_tokens: int,
                              timeout: int,
                              provider_type: ProviderType) -> Optional[LLMResponse]:
        """
        Get a completion from Google.
        
        Args:
            client: The Google client.
            messages: List of message dictionaries.
            model: The model to use.
            temperature: The temperature to use.
            max_tokens: The maximum number of tokens to generate.
            timeout: The timeout in seconds.
            provider_type: The provider type.
        
        Returns:
            An LLMResponse object, or None if the request failed.
        """
        # Initialize Google model
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        # Handle potentially empty safety settings for newer models
        if "gemini-2.0" in model or "gemini-2.5" in model:
            # For Gemini 2.0 and 2.5 models, we need to set safety settings explicitly
            safety_settings = {
                # Add minimal safety settings to avoid causing issues
                "HARASSMENT": "block_none",
                "HATE": "block_none",
                "SEXUAL": "block_none",
                "DANGEROUS": "block_none"
            }
            google_model = client.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
        else:
            # For older models, use default safety settings
            google_model = client.GenerativeModel(
                model_name=model,
                generation_config=generation_config
            )
        
        # Convert messages to Google format
        gemini_messages = []
        system_content = ""
        
        # Extract system messages first
        for msg in messages:
            if msg.get("role") == "system":
                system_content += msg.get("content", "") + "\n"
        
        # Add system content as a prefix to the first user message if any
        user_msg_found = False
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                if not user_msg_found and system_content:
                    # Add system content to first user message
                    content = system_content + "\n\n" + content
                    system_content = ""
                    user_msg_found = True
                
                # Ensure content is not empty
                if not content.strip():
                    content = "Hello, please respond."
                    
                gemini_messages.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                # Ensure content is not empty
                if not content.strip():
                    continue  # Skip empty assistant messages
                    
                gemini_messages.append({"role": "model", "parts": [content]})
        
        # Make sure we have at least one user message
        if not user_msg_found and system_content:
            gemini_messages.append({"role": "user", "parts": [system_content]})
        
        # Make sure we have at least one message
        if not gemini_messages:
            gemini_messages.append({"role": "user", "parts": ["Hello, please respond."]})
        
        # Generate a response
        # Debugging the exact message format sent
        logger.debug(f"Sending Gemini messages: {json.dumps(gemini_messages, indent=2)}")
        
        # Handle message formatting based on Gemini model
        try:
            if "gemini-2.0" in model:
                if len(gemini_messages) == 1:
                    # For single messages with newer Gemini models
                    content = gemini_messages[0]["parts"][0]
                    response = google_model.generate_content(content)
                else:
                    # For conversations with newer Gemini models
                    # Convert to Google's newer chat format
                    chat = []
                    for msg in gemini_messages:
                        if msg["role"] == "user":
                            chat.append({"role": "user", "parts": [{"text": msg["parts"][0]}]})
                        elif msg["role"] == "model":
                            chat.append({"role": "model", "parts": [{"text": msg["parts"][0]}]})
                    
                    response = google_model.generate_content(chat)
            else:
                # For older Gemini models
                response = google_model.generate_content(gemini_messages)
        except Exception as e:
            # Fallback to the simplest possible request
            logger.warning(f"Error with standard Gemini format: {e}. Trying fallback format...")
            
            # Create a simple prompt from the messages
            combined_prompt = ""
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if content:
                    combined_prompt += f"{role}: {content}\n\n"
            
            if not combined_prompt:
                combined_prompt = "Hello, please respond."
                
            response = google_model.generate_content(combined_prompt)
        
        # Parse the response
        try:
            content = response.text
            
            # Google doesn't provide token usage in the response
            # We can estimate based on content length
            prompt_tokens = sum(len(msg.get("content", "")) for msg in messages) // 4  # Rough estimate
            completion_tokens = len(content) // 4  # Rough estimate
            total_tokens = prompt_tokens + completion_tokens
            
            # Log completion
            if self._llm_settings.get("log_completions", True):
                logger.debug(f"LLM Completion: provider={provider_type.name}, model={model}, est_tokens={total_tokens}")
                logger.debug(f"  content: {content[:100]}...")
            
            # Calculate cost (this is an approximation)
            cost = self._calculate_cost(model, prompt_tokens, completion_tokens, provider_type)
            
            return LLMResponse(
                content=content,
                provider_type=provider_type,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                finish_reason="stop"
            )
            
        except Exception as e:
            logger.error(f"Error parsing Google response: {e}")
            return None
    
    def _calculate_cost(self, 
                       model: str, 
                       prompt_tokens: int, 
                       completion_tokens: int,
                       provider_type: ProviderType) -> float:
        """
        Calculate the cost of a completion.
        
        Args:
            model: The model used.
            prompt_tokens: The number of prompt tokens.
            completion_tokens: The number of completion tokens.
            provider_type: The provider type.
        
        Returns:
            The cost in USD.
        """
        # Define pricing by provider and model
        # These are approximate and may need to be updated
        pricing = {
            ProviderType.OPENAI: {
                "gpt-4o-mini": {
                    "prompt": 0.0015,  # per 1000 tokens
                    "completion": 0.002  # per 1000 tokens
                },
                "gpt-4o": {
                    "prompt": 0.03,  # per 1000 tokens
                    "completion": 0.06  # per 1000 tokens
                }
            },
            ProviderType.ANTHROPIC: {
                "claude-3-7-sonnet-latest": {
                    "prompt": 0.01,  # per 1000 tokens
                    "completion": 0.03  # per 1000 tokens
                },
                "claude-3-5-haiku-latest": {
                    "prompt": 0.0015,  # per 1000 tokens
                    "completion": 0.0055  # per 1000 tokens
                }
            },
            ProviderType.GOOGLE: {
                "gemini-pro": {
                    "prompt": 0.0005,  # per 1000 tokens
                    "completion": 0.0015  # per 1000 tokens
                }
            },
            ProviderType.OPENROUTER: {
                # OpenRouter has variable pricing; using approximations
                "google/gemini-2.0-flash-lite-preview-02-05:free": {
                    "prompt": 0.0,  # per 1000 tokens
                    "completion": 0.0  # per 1000 tokens
                },
                "nousresearch/deephermes-3-llama-3-8b-preview:free": {
                    "prompt": 0.0,  # per 1000 tokens
                    "completion": 0.0  # per 1000 tokens
                },
                "google/gemini-2.0-pro-exp-02-05:free": {
                    "prompt": 0.0,  # per 1000 tokens
                    "completion": 0.0 # per 1000 tokens
                },
                "mistralai/mistral-small-3.1-24b-instruct:free": {
                    "prompt": 0.0,  # per 1000 tokens
                    "completion": 0.0  # per 1000 tokens
                },
                "mistralai/mistral-small-3.1-24b-instruct:free": {
                    "prompt": 0.0,  # per 1000 tokens
                    "completion": 0.0  # per 1000 tokens
                }
            }
        }
        
        # Get pricing for the model
        provider_pricing = pricing.get(provider_type, {})
        model_pricing = provider_pricing.get(model, None)
        
        if model_pricing is None:
            # Use default pricing if the model is not found
            model_pricing = {"prompt": 0.001, "completion": 0.002}
        
        # Calculate cost
        prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * model_pricing["completion"]
        
        return prompt_cost + completion_cost
    
    def run_llm_diagnostics(self) -> Dict[str, Any]:
        """
        Run diagnostics on available LLM providers.
        
        Returns:
            Dictionary with diagnostic results.
        """
        results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "providers": {}
        }
        
        # Check available providers
        available_providers = self._provider_manager.get_available_providers()
        
        if not available_providers:
            logger.warning("No LLM providers available")
            results["status"] = "error"
            results["error"] = "No LLM providers available"
            return results
        
        # Test each available provider
        for provider in available_providers:
            provider_name = provider.name
            
            logger.info(f"Testing LLM provider: {provider_name}")
            
            # Verify the client
            client_ok = self._provider_manager.verify_client(provider)
            
            if not client_ok:
                logger.warning(f"Provider {provider_name} client verification failed")
                results["providers"][provider_name] = {
                    "status": "error",
                    "error": "Client verification failed"
                }
                continue
            
            # Test a simple completion
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, world! Please respond with 'Hello from the LLM!'"}
            ]
            
            try:
                response = self.get_completion(
                    messages=test_messages,
                    provider_type=provider,
                    temperature=0.0,  # Use deterministic output for testing
                    max_tokens=20,
                    timeout=30,
                    retry_attempts=1
                )
                
                if response:
                    logger.info(f"Provider {provider_name} test successful")
                    
                    results["providers"][provider_name] = {
                        "status": "success",
                        "model": response.model,
                        "response_content": response.content.strip(),
                        "tokens": {
                            "prompt": response.prompt_tokens,
                            "completion": response.completion_tokens,
                            "total": response.total_tokens
                        },
                        "cost": response.cost
                    }
                else:
                    logger.warning(f"Provider {provider_name} test failed: No response")
                    
                    results["providers"][provider_name] = {
                        "status": "error",
                        "error": "No response from LLM"
                    }
            
            except Exception as e:
                logger.error(f"Provider {provider_name} test error: {e}")
                
                results["providers"][provider_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Overall status
        success_count = sum(1 for p in results["providers"].values() if p.get("status") == "success")
        
        if success_count > 0:
            results["status"] = "success"
            results["message"] = f"{success_count}/{len(results['providers'])} providers operational"
        else:
            results["status"] = "error"
            results["message"] = "No operational providers found"
        
        # Log summary
        logger.info(f"LLM diagnostics complete: {results['message']}")
        
        return results


# Convenience function
def get_llm_manager() -> LLMManager:
    """Get the LLM manager instance."""
    return LLMManager()


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logger.basicConfig(level=logger.INFO)
    
    # Create the LLM manager
    manager = get_llm_manager()
    
    # Run diagnostics
    diagnostics = manager.run_llm_diagnostics()
    print(f"Diagnostics: {diagnostics['status']} - {diagnostics['message']}")
    
    # Test completion
    messages = [
        {"role": "system", "content": "You are a helpful assistant for an RPG game."},
        {"role": "user", "content": "Describe a small village."}
    ]
    
    response = manager.get_completion(messages)
    
    if response:
        print(f"Response from {response.provider_type.name} ({response.model}):")
        print(response.content)
        print(f"Tokens: {response.total_tokens} (${response.cost:.6f})")
    else:
        print("No response from LLM.")