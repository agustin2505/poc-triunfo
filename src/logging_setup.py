"""Configuración de logging centralizada."""
import logging
import os
from datetime import datetime
from collections import deque

# Almacenar últimos N logs en memoria para endpoint /logs
MAX_MEMORY_LOGS = 100
memory_logs = deque(maxlen=MAX_MEMORY_LOGS)


class MemoryHandler(logging.Handler):
    """Handler que guarda logs en memoria."""
    def emit(self, record):
        try:
            msg = self.format(record)
            memory_logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": msg,
            })
        except Exception:
            self.handleError(record)


def setup_logging(name: str, log_file: str = "logs/triunfo.log") -> logging.Logger:
    """Configura logging para un módulo."""
    os.makedirs(os.path.dirname(log_file) or "logs", exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Evitar handlers duplicados
    if logger.handlers:
        return logger

    # Formato detallado
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler: Console (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler: Archivo
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"No se pudo crear file handler: {e}")

    # Handler: Memoria (para endpoint /logs)
    memory_handler = MemoryHandler()
    memory_handler.setLevel(logging.DEBUG)
    memory_handler.setFormatter(formatter)
    logger.addHandler(memory_handler)

    return logger


def get_memory_logs():
    """Retorna los últimos logs de memoria."""
    return list(memory_logs)
