"""aiohttp-сервер для приёма вебхуков CryptoBot (Crypto Pay)."""
import logging
from aiohttp import web
from aiogram import Bot

import database as db
from config import config
from utils.cryptobot import verify_webhook_signature

logger = logging.getLogger(__name__)


async def cryptobot_webhook(request: web.Request) -> web.Response:
    raw_body = await request.read()
    signature = request.headers.get("crypto-pay-api-signature", "")

    if not verify_webhook_signature(raw_body, signature):
        logger.warning("CryptoBot webhook: invalid signature")
        return web.Response(status=403, text="Invalid signature")

    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Bad JSON")

    update_type = data.get("update_type")
    logger.info("CryptoBot webhook: update_type=%s", update_type)

    if update_type != "invoice_paid":
        return web.Response(status=200, text="OK")

    invoice = data.get("payload", {})
    order_id    = invoice.get("payload")          # мы кладём order_id в поле payload
    invoice_id  = str(invoice.get("invoice_id", ""))
    # Сумма в рублях: fiat amount
    amount_str  = invoice.get("amount", "0")

    if not order_id:
        logger.warning("CryptoBot webhook: no order_id in payload")
        return web.Response(status=200, text="OK")

    payment = await db.get_payment_by_order(order_id)
    if not payment:
        logger.warning("CryptoBot webhook: payment not found for order %s", order_id)
        return web.Response(status=200, text="OK")

    if payment["status"] == "paid":
        return web.Response(status=200, text="OK")  # идемпотентность

    # Зачисляем оригинальную сумму из БД (без комиссии),
    # а не amount от CryptoBot (который включает комиссию)
    credit_amount = float(payment["amount"])

    await db.update_payment_status(order_id, "paid", invoice_id)
    new_balance = await db.update_balance(payment["user_id"], credit_amount)
    await db.add_log(
        payment["user_id"],
        "topup_webhook",
        f"+{credit_amount:.2f} ₽ via CryptoBot, invoice={invoice_id}, order={order_id}"
    )
    logger.info("Credited %.2f RUB to user #%s", credit_amount, payment["user_id"])

    # Уведомляем пользователя в Telegram
    bot: Bot = request.app["bot"]
    try:
        await bot.send_message(
            payment["user_id"],
            f"✅ <b>Баланс пополнен!</b>\n\n"
            f"Зачислено: <b>+{credit_amount:.2f} ₽</b>\n"
            f"Текущий баланс: <b>{new_balance:.2f} ₽</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning("Failed to notify user #%s: %s", payment["user_id"], e)

    return web.Response(status=200, text="OK")


def create_webhook_app(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post(config.webhook_path, cryptobot_webhook)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    return app
