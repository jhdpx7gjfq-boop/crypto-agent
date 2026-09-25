"""
Structured logging for IGWT-PF26.

Every pipeline event must expose:
- timestamp
- component
- event
- status
- context (symbol, version, etc.)
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional, Dict


class StructuredFormatter(logging.Formatter):
    """JSON structured logging formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }

        # Preserve extra fields if provided
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "symbol"):
            log_data["symbol"] = record.symbol
        if hasattr(record, "timeframe"):
            log_data["timeframe"] = record.timeframe
        if hasattr(record, "version"):
            log_data["version"] = record.version
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "record_count"):
            log_data["record_count"] = record.record_count

        # Add error context if present
        if record.exc_info:
            log_data["error"] = self.formatException(record.exc_info)
        elif hasattr(record, "error") and record.error:
            log_data["error"] = str(record.error)

        return json.dumps(log_data)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create a structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

    return logger


def log_event(
    logger: logging.Logger,
    event: str,
    status: str,
    **context: Any,
) -> None:
    """
    Log a structured event with context.

    Example:
        log_event(logger, "fetch_complete", "success",
                  symbol="BTC", timeframe="1d", record_count=500)
    """
    record = logging.LogRecord(
        name=logger.name,
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    )

    record.event = event
    record.status = status
    for key, value in context.items():
        setattr(record, key, value)

    logger.handle(record)
