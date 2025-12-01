import re
from datetime import datetime
from typing import Optional, List

from core.utils.logging_config import get_logger
from .log_entry import LogEntry

logger = get_logger("LogViewerTool.Parser")

class LogParser:
    """
    Parses log lines into LogEntry objects.
    Expected format: YYYY-MM-DD HH:MM:SS [LOGGER_NAME] LOG_LEVEL: Message
    """
    # Regex to capture the components of a log line
    # Handles optional milliseconds in timestamp
    LOG_LINE_REGEX = re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?)\s+"
        r"\[(?P<logger_name>[^\]]+)\]\s+"
        r"(?P<level>\w+):\s+"
        r"(?P<message>.+)$"
    )
    # Simpler timestamp format without milliseconds, if needed as fallback
    TIMESTAMP_FORMAT_NO_MS = "%Y-%m-%d %H:%M:%S"
    TIMESTAMP_FORMAT_WITH_MS = "%Y-%m-%d %H:%M:%S,%f"


    @staticmethod
    def parse_line(line: str) -> Optional[LogEntry]:
        """
        Parses a single log line.

        Args:
            line: The log line string.

        Returns:
            A LogEntry object if parsing is successful, None otherwise.
        """
        match = LogParser.LOG_LINE_REGEX.match(line.strip())
        if not match:
            # Attempt to handle lines that might be continuations or not fit the pattern
            # For now, we'll treat them as messages from a "RAW" logger or skip them
            # logger.debug(f"Line does not match expected log format: {line.strip()}")
            return None # Or create a LogEntry with default/RAW values if desired

        parts = match.groupdict()
        
        timestamp_str = parts["timestamp"]
        dt_object = None
        try:
            # Try parsing with milliseconds first
            dt_object = datetime.strptime(timestamp_str, LogParser.TIMESTAMP_FORMAT_WITH_MS)
        except ValueError:
            try:
                # Fallback to parsing without milliseconds
                dt_object = datetime.strptime(timestamp_str, LogParser.TIMESTAMP_FORMAT_NO_MS)
            except ValueError:
                logger.warning(f"Could not parse timestamp: {timestamp_str}. Using current time as fallback.")
                dt_object = datetime.now() # Fallback, less ideal

        return LogEntry(
            timestamp=dt_object,
            logger_name=parts["logger_name"].strip(),
            level=parts["level"].strip().upper(), # Normalize level to uppercase
            message=parts["message"].strip(),
            raw_line=line.strip()
        )

    @staticmethod
    def parse_file_content(content: str) -> List[LogEntry]:
        """
        Parses the entire content of a log file.

        Args:
            content: A string containing all lines of a log file.

        Returns:
            A list of LogEntry objects.
        """
        log_entries: List[LogEntry] = []
        for line in content.splitlines():
            entry = LogParser.parse_line(line)
            if entry:
                log_entries.append(entry)
        return log_entries