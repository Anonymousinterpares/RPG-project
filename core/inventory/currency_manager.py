#!/usr/bin/env python3
"""
Currency management module.

This module provides functionality for managing in-game currency.
"""

from typing import Dict, Optional, Tuple
import logging

from core.utils.logging_config import get_logger

# Get module logger
logger = get_logger("Inventory")


class CurrencyManager:
    """
    Manager for in-game currency.
    
    This class handles operations related to currency, including
    conversions and transactions.
    """
    
    def __init__(self):
        """Initialize the currency manager."""
        # Initialize currency values
        self._copper: int = 0
        
        # Currency conversion rates
        self._copper_per_silver: int = 100
        self._silver_per_gold: int = 100
        
        logger.info("Currency manager initialized")
    
    @property
    def copper(self) -> int:
        """Get the total currency value in copper."""
        return self._copper
    
    @property
    def silver(self) -> int:
        """Get the silver component of the currency."""
        return (self._copper // self._copper_per_silver) % self._silver_per_gold
    
    @property
    def gold(self) -> int:
        """Get the gold component of the currency."""
        return self._copper // (self._copper_per_silver * self._silver_per_gold)
    
    def get_formatted_currency(self) -> str:
        """
        Get a formatted string representation of the currency.
        
        Returns:
            String in the format "X gold, Y silver, Z copper".
        """
        result = []
        
        gold_value = self.gold
        silver_value = self.silver
        copper_value = self._copper % self._copper_per_silver
        
        if gold_value > 0:
            result.append(f"{gold_value} gold")
        
        if silver_value > 0 or (gold_value > 0 and copper_value > 0):
            result.append(f"{silver_value} silver")
        
        if copper_value > 0 or not result:
            result.append(f"{copper_value} copper")
        
        return ", ".join(result)
    
    def get_currency_dict(self) -> Dict[str, int]:
        """
        Get the currency values as a dictionary.
        
        Returns:
            Dictionary with gold, silver, and copper values.
        """
        return {
            "gold": self.gold,
            "silver": self.silver,
            "copper": self._copper % self._copper_per_silver,
            "total_copper": self._copper
        }
    
    def add_currency(self, amount: int) -> bool:
        """
        Add currency (in copper).
        
        Args:
            amount: The amount to add in copper.
            
        Returns:
            True if the currency was added successfully.
        """
        if amount <= 0:
            logger.warning(f"Cannot add non-positive currency amount: {amount}")
            return False
        
        self._copper += amount
        logger.info(f"Added {amount} copper to currency")
        return True
    
    def remove_currency(self, amount: int) -> bool:
        """
        Remove currency (in copper).
        
        Args:
            amount: The amount to remove in copper.
            
        Returns:
            True if the currency was removed successfully, False if insufficient funds.
        """
        if amount <= 0:
            logger.warning(f"Cannot remove non-positive currency amount: {amount}")
            return False
        
        if amount > self._copper:
            logger.warning(f"Insufficient funds: {self._copper} copper available, {amount} copper required")
            return False
        
        self._copper -= amount
        logger.info(f"Removed {amount} copper from currency")
        return True
    
    def add_mixed_currency(self, gold: int = 0, silver: int = 0, copper: int = 0) -> bool:
        """
        Add currency using mixed denominations.
        
        Args:
            gold: Amount of gold to add.
            silver: Amount of silver to add.
            copper: Amount of copper to add.
            
        Returns:
            True if the currency was added successfully.
        """
        if gold < 0 or silver < 0 or copper < 0:
            logger.warning(f"Cannot add negative currency amounts: {gold}g, {silver}s, {copper}c")
            return False
        
        if gold == 0 and silver == 0 and copper == 0:
            return True
        
        total_copper = (gold * self._copper_per_silver * self._silver_per_gold) + \
                       (silver * self._copper_per_silver) + \
                       copper
        
        return self.add_currency(total_copper)
    
    def remove_mixed_currency(self, gold: int = 0, silver: int = 0, copper: int = 0) -> bool:
        """
        Remove currency using mixed denominations.
        
        Args:
            gold: Amount of gold to remove.
            silver: Amount of silver to remove.
            copper: Amount of copper to remove.
            
        Returns:
            True if the currency was removed successfully, False if insufficient funds.
        """
        if gold < 0 or silver < 0 or copper < 0:
            logger.warning(f"Cannot remove negative currency amounts: {gold}g, {silver}s, {copper}c")
            return False
        
        if gold == 0 and silver == 0 and copper == 0:
            return True
        
        total_copper = (gold * self._copper_per_silver * self._silver_per_gold) + \
                       (silver * self._copper_per_silver) + \
                       copper
        
        return self.remove_currency(total_copper)
    
    def has_enough_currency(self, amount: int) -> bool:
        """
        Check if there is enough currency available.
        
        Args:
            amount: The amount to check in copper.
            
        Returns:
            True if there is enough currency, False otherwise.
        """
        return self._copper >= amount
    
    def has_enough_mixed_currency(self, gold: int = 0, silver: int = 0, copper: int = 0) -> bool:
        """
        Check if there is enough currency available using mixed denominations.
        
        Args:
            gold: Amount of gold to check.
            silver: Amount of silver to check.
            copper: Amount of copper to check.
            
        Returns:
            True if there is enough currency, False otherwise.
        """
        total_copper = (gold * self._copper_per_silver * self._silver_per_gold) + \
                       (silver * self._copper_per_silver) + \
                       copper
        
        return self.has_enough_currency(total_copper)
    
    def set_currency(self, amount: int) -> None:
        """
        Set the total currency to a specific amount (in copper).
        
        Args:
            amount: The amount to set in copper.
        """
        if amount < 0:
            logger.warning(f"Cannot set currency to negative value: {amount}")
            self._copper = 0
        else:
            self._copper = amount
            logger.info(f"Set currency to {amount} copper")
    
    def set_mixed_currency(self, gold: int = 0, silver: int = 0, copper: int = 0) -> None:
        """
        Set the currency using mixed denominations.
        
        Args:
            gold: Amount of gold to set.
            silver: Amount of silver to set.
            copper: Amount of copper to set.
        """
        if gold < 0 or silver < 0 or copper < 0:
            logger.warning(f"Cannot set negative currency amounts: {gold}g, {silver}s, {copper}c")
            self._copper = 0
            return
        
        total_copper = (gold * self._copper_per_silver * self._silver_per_gold) + \
                       (silver * self._copper_per_silver) + \
                       copper
        
        self.set_currency(total_copper)
