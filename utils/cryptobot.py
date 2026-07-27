"""Клиент CryptoBot (Crypto Pay) API."""
import hashlib
import hmac
import logging
from typing import Optional, Dict, Any, List

import aiohttp

from config import config

logger = logging.getLogger(__name__)

# Mainnet: https://pay.crypt.bot  |  Testnet: https://testnet-pay.crypt.bot
BASE_URL = "https://testnet-pay.crypt.bot" if config.cryptobot_testnet else "https://pay.crypt.bot"


def _headers() -> Dict[str, str]:
    return {
        "Crypto-Pay-API-Token": config.cryptobot_token,
        "Content-Type": "application/json",
    }


async def _post(method: str, **params) -> Optional[Dict[str, Any]]:
    url = f"{BASE_URL}/api/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=params,
                headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("result")
                logger.error("CryptoBot %s error: %s", method, data)
                return None
    except Exception as exc:
        logger.exception("CryptoBot %s exception: %s", method, exc)
        return None


async def _get(method: str, **params) -> Optional[Any]:
    url = f"{BASE_URL}/api/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("result")
                logger.error("CryptoBot %s error: %s", method, data)
                return None
    except Exception as exc:
        logger.exception("CryptoBot %s exception: %s", method, exc)
        return None


# ── Публичные методы ─────────────────────────────────────────────────────────

async def create_invoice(
    amount_rub: float,
    order_id: str,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Создаёт счёт на оплату в рублях. Пользователь платит любой криптовалютой.
    Возвращает объект Invoice с полем bot_invoice_url.
    """
    result = await _post(
        "createInvoice",
        currency_type="fiat",
        fiat="RUB",
        amount=f"{amount_rub:.2f}",
        description=f"Пополнение баланса Selectel Market",
        payload=order_id,               # вернётся в вебхуке — используем как order_id
        expires_in=1800,                # 30 минут
        allow_comments=False,
        allow_anonymous=True,
    )
    return result


async def get_invoice(invoice_id: int) -> Optional[Dict[str, Any]]:
    """Запрашивает счёт по его ID."""
    result = await _get("getInvoices", invoice_ids=str(invoice_id), count=1)
    if result and isinstance(result, dict):
        items = result.get("items", [])
        return items[0] if items else None
    return None


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """
    Проверяет подпись вебхука CryptoBot.
    secret = SHA256(token)
    expected = HMAC-SHA256(secret, raw_body).hexdigest()
    """
    if not config.cryptobot_token:
        logger.warning("CRYPTOBOT_TOKEN not set — skipping webhook signature check")
        return True
    secret = hashlib.sha256(config.cryptobot_token.encode()).digest()
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
