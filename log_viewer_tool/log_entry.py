from dataclasses import dataclass
from datetime import datetime

@dataclass
class LogEntry:
    """
    Represents a single parsed log entry.
    """
    timestamp: datetime
    logger_name: str
    level: str
    message: str
    raw_line: str # Store the original line for export if needed