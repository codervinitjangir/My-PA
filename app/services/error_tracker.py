import logging
import traceback
import collections
import datetime
from typing import List, Dict, Any

class ErrorTracker(logging.Handler):
    """
    A custom logging handler that keeps recent error records in memory.
    It groups errors by their traceback (or exception type) to find recurring issues.
    """
    def __init__(self, max_history=1000):
        super().__init__()
        self.error_history = collections.deque(maxlen=max_history)
        
    def emit(self, record: logging.LogRecord):
        # We only care about ERROR or CRITICAL level
        if record.levelno < logging.ERROR:
            return
            
        # Extract traceback if present
        exc_info = record.exc_info
        tb_text = None
        
        if exc_info:
            tb_text = "".join(traceback.format_exception(*exc_info))
        elif record.exc_text:
            tb_text = record.exc_text
            
        # Some errors might just be string messages without a traceback.
        # We'll use the message itself as a fallback identifier.
        identifier = tb_text if tb_text else record.getMessage()
            
        error_entry = {
            "timestamp": datetime.datetime.now(),
            "message": record.getMessage(),
            "traceback": tb_text,
            "identifier": identifier,
            "logger_name": record.name
        }
        
        self.error_history.append(error_entry)

    def get_recurring_errors(self, threshold=3, timeframe_minutes=60) -> List[Dict[str, Any]]:
        """
        Finds errors that have occurred `threshold` or more times in the last `timeframe_minutes`.
        """
        now = datetime.datetime.now()
        cutoff_time = now - datetime.timedelta(minutes=timeframe_minutes)
        
        # Count occurrences of each identifier
        recent_errors = [e for e in self.error_history if e["timestamp"] >= cutoff_time]
        
        counts = collections.defaultdict(list)
        for error in recent_errors:
            counts[error["identifier"]].append(error)
            
        recurring_errors = []
        for identifier, occurrences in counts.items():
            if len(occurrences) >= threshold:
                latest_error = occurrences[-1]
                if latest_error["traceback"]:
                    recurring_errors.append({
                        "count": len(occurrences),
                        "latest_timestamp": latest_error["timestamp"],
                        "message": latest_error["message"],
                        "traceback": latest_error["traceback"],
                        "identifier": identifier,
                        "logger_name": latest_error["logger_name"]
                    })
                    
        return recurring_errors

# Singleton instance to be used across the app
global_error_tracker = ErrorTracker()
