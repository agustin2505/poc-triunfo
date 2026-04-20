"""Descarga de archivos desde los servidores de Telegram — Spec-22."""
from __future__ import annotations

import os

from src.logging_setup import setup_logging

logger = setup_logging("triunfo.telegram.downloader")

SUPPORTED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
SUPPORTED_MIME_TYPES = SUPPORTED_IMAGE_MIME_TYPES | {"application/pdf"}


class TelegramDownloadError(Exception):
    pass


async def download_telegram_file(file_id: str, bot) -> bytes:
    """Descarga un archivo de Telegram por su file_id y retorna los bytes."""
    max_bytes = int(os.getenv("TELEGRAM_MAX_FILE_SIZE_MB", "20")) * 1024 * 1024
    try:
        tg_file = await bot.get_file(file_id)
        if tg_file.file_size and tg_file.file_size > max_bytes:
            raise TelegramDownloadError(
                f"Archivo de {tg_file.file_size // (1024*1024)}MB supera el límite de "
                f"{os.getenv('TELEGRAM_MAX_FILE_SIZE_MB', '20')}MB"
            )
        data = await tg_file.download_as_bytearray()
        return bytes(data)
    except TelegramDownloadError:
        raise
    except Exception as e:
        raise TelegramDownloadError(f"Error descargando archivo: {e}") from e
