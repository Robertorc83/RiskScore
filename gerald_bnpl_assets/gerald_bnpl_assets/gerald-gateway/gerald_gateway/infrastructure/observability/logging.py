"""Structured JSON logging for production observability"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with timestamp and service metadata"""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["service"] = "gerald-gateway"


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging"""
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # JSON handler for stdout
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log_decision(
    request_id: str,
    user_id: str,
    approved: bool,
    credit_limit_cents: int,
    duration_ms: float,
) -> None:
    """Log structured decision outcome for analysis"""
    logging.info(
        "Decision completed",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "step": "decision_complete",
            "approval_outcome": "approved" if approved else "declined",
            "credit_limit_cents": credit_limit_cents,
            "duration_ms": duration_ms,
        },
    )
