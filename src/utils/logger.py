"""Configuracao de logging estruturado para o pipeline."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Serializa eventos de log em JSON para uso em automacao."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "event_data") and isinstance(record.event_data, dict):
            payload.update(record.event_data)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def get_logger(name: str, json_logs: bool = False) -> logging.Logger:
    """Cria logger com formato simples ou estruturado."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonLogFormatter()
        if json_logs
        else logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, message: str, **event_data: Any) -> None:
    """Envia um evento com metadados adicionais de forma consistente."""
    logger.info(message, extra={"event_data": event_data})