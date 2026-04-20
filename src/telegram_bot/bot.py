"""Ciclo de vida del bot de Telegram — Spec-21."""
from __future__ import annotations

import asyncio
import os
import traceback
from typing import Optional

from src.logging_setup import setup_logging

logger = setup_logging("triunfo.telegram.bot")


class TelegramBot:
    def __init__(self) -> None:
        self._app = None
        self._mode: str = "disabled"
        self._polling_task: Optional[asyncio.Task] = None

    async def initialize(self, fastapi_app) -> None:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN no configurado — bot deshabilitado")
            return

        from telegram.ext import ApplicationBuilder
        self._app = ApplicationBuilder().token(token).build()
        self._register_handlers()
        await self._app.initialize()
        await self._app.start()

        mode = os.getenv("TELEGRAM_MODE", "polling").lower()
        if mode == "webhook":
            await self._setup_webhook()
            self._mode = "webhook"
        else:
            await self._app.updater.start_polling()
            self._mode = "polling"
            logger.info("Polling de Telegram iniciado")

        logger.info(f"Bot de Telegram listo en modo {self._mode}")

    async def _setup_webhook(self) -> None:
        webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "").rstrip("/")
        secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "") or None
        if not webhook_url:
            logger.error("TELEGRAM_WEBHOOK_URL vacío en modo webhook — webhook no registrado")
            return
        full_url = f"{webhook_url}/telegram/webhook"
        await self._app.bot.set_webhook(url=full_url, secret_token=secret)
        logger.info(f"Webhook registrado: {full_url}")

    def _register_handlers(self) -> None:
        from telegram.ext import (
            CallbackQueryHandler,
            CommandHandler,
            MessageHandler,
            filters,
        )
        from src.telegram_bot import handlers

        # Comandos — primero para que tengan prioridad
        self._app.add_handler(CommandHandler("start", handlers.cmd_start))
        self._app.add_handler(CommandHandler(["ayuda", "help"], handlers.cmd_ayuda))
        self._app.add_handler(CommandHandler("estado", handlers.cmd_estado))
        self._app.add_handler(CommandHandler("aprobar", handlers.cmd_aprobar))
        self._app.add_handler(CommandHandler("rechazar", handlers.cmd_rechazar))

        # Callbacks de botones inline
        self._app.add_handler(
            CallbackQueryHandler(handlers.handle_inline_callback, pattern=r"^(aprobar|rechazar):")
        )

        # Mensajes con adjuntos — al final
        self._app.add_handler(MessageHandler(filters.PHOTO, handlers.on_photo))
        self._app.add_handler(MessageHandler(filters.Document.ALL, handlers.on_document))

    async def shutdown(self) -> None:
        if self._app is None:
            return
        try:
            if self._mode == "polling" and self._app.updater:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            logger.info("Bot de Telegram detenido")
        except Exception:
            logger.error("Error al detener el bot:\n" + traceback.format_exc())

    def get_application(self):
        return self._app

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_connected(self) -> bool:
        return self._app is not None
