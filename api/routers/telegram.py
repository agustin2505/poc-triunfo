"""Router de Telegram: webhook y status — Spec-21."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request

from src.logging_setup import setup_logging

logger = setup_logging("triunfo.telegram.router")
router = APIRouter(prefix="/telegram", tags=["Telegram"])


def _get_telegram_bot(request: Request):
    return getattr(request.app.state, "telegram_bot", None)


@router.post("/webhook", summary="Recibir updates de Telegram (modo webhook)")
async def telegram_webhook(request: Request):
    telegram_bot = _get_telegram_bot(request)
    if telegram_bot is None:
        return {"ok": True}

    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if secret:
        incoming = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if incoming != secret:
            raise HTTPException(status_code=403, detail="Forbidden")

    app = telegram_bot.get_application()
    if app is None:
        return {"ok": True}

    from telegram import Update
    body = await request.json()
    update = Update.de_json(body, app.bot)
    await app.process_update(update)
    return {"ok": True}


@router.get("/status", summary="Estado del bot de Telegram")
async def telegram_status(request: Request):
    telegram_bot = _get_telegram_bot(request)

    if telegram_bot is None or telegram_bot.mode == "disabled":
        return {
            "mode": "disabled",
            "connected": False,
            "bot_username": None,
            "webhook_url": None,
            "last_update_at": None,
        }

    app = telegram_bot.get_application()
    bot_username = None
    if app:
        try:
            me = await app.bot.get_me()
            bot_username = f"@{me.username}"
        except Exception:
            pass

    return {
        "mode": telegram_bot.mode,
        "connected": telegram_bot.is_connected,
        "bot_username": bot_username,
        "webhook_url": os.getenv("TELEGRAM_WEBHOOK_URL") or None,
        "last_update_at": None,
    }
