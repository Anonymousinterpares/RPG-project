#!/usr/bin/env python3
"""
Item statistics module.

This module defines the ItemStat class used to represent
attributes and properties of items.
"""

from dataclasses import dataclass
from typing import Dict, Union, Optional, Any


@dataclass
class ItemStat:
    """A stat or attribute of an item."""
    name: str
    value: Union[int, float, str, bool]
    display_name: Optional[str] = None
    is_percentage: bool = False
    
    def __str__(self) -> str:
        """Return a display-friendly string representation."""
        display = self.display_name or self.name.replace('_', ' ').title()
        if isinstance(self.value, (int, float)):
            if self.is_percentage:
                return f"{display}: {self.value:+.1f}%"
            return f"{display}: {self.value:+.1f}"
        return f"{display}: {self.value}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "display_name": self.display_name,
            "is_percentage": self.is_percentage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ItemStat':
        """Create an ItemStat from a dictionary."""
        return cls(
            name=data["name"],
            value=data["value"],
            display_name=data.get("display_name"),
            is_percentage=data.get("is_percentage", False)
        )
