"""Хендлер профиля пользователя."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import profile_kb, back_to_main_kb
from utils.photo import send_banner, edit_banner

router = Router()


def profile_text(user: dict, last_order: dict | None) -> str:
    balance = user.get("balance", 0.0)
    created = user.get("created_at", "—")[:10]
    last_purchase = "—"
    if last_order:
        last_purchase = f"{last_order.get('title', '?')} ({last_order.get('created_at', '')[:10]})"

    username = f"@{user['username']}" if user.get("username") else "нет"

    return (
        f"<b>👤 Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user['id']}</code>\n"
        f"👥 Username: {username}\n"
        f"💳 Баланс: <b>{balance:.2f} ₽</b>\n"
        f"📅 Дата регистрации: {created}\n"
        f"📦 Последняя покупка: {last_purchase}\n"
    )


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message, db_user: dict):
    if not db_user.get("agreed_tos"):
        await message.answer("Сначала примите пользовательское соглашение: /start")
        return
    user = await db.get_user(message.from_user.id)
    last_order = await db.get_last_order(message.from_user.id)
    await send_banner(message, profile_text(user, last_order), reply_markup=profile_kb())


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(call: CallbackQuery, db_user: dict):
    user = await db.get_user(call.from_user.id)
    last_order = await db.get_last_order(call.from_user.id)
    await edit_banner(call, profile_text(user, last_order), reply_markup=profile_kb())


@router.callback_query(F.data == "my_orders")
async def my_orders(call: CallbackQuery):
    import aiosqlite
    from config import config

    async with aiosqlite.connect(config.db_path) as db_conn:
        db_conn.row_factory = aiosqlite.Row
        cursor = await db_conn.execute(
            """SELECT o.id, o.amount, o.created_at, a.title
               FROM orders o JOIN accounts a ON a.id = o.account_id
               WHERE o.user_id = ?
               ORDER BY o.created_at DESC LIMIT 10""",
            (call.from_user.id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        await edit_banner(
            call,
            "📭 <b>У вас пока нет покупок.</b>\n\nЗайдите в раздел «📦 Купить аккаунты».",
            reply_markup=back_to_main_kb(),
        )
        return

    lines = ["<b>🗳 История покупок (последние 10):</b>\n"]
    for r in rows:
        lines.append(
            f"• <b>{r['title']}</b>  —  {r['amount']:.2f} ₽  "
            f"<i>({r['created_at'][:10]})</i>"
        )

    await edit_banner(call, "\n".join(lines), reply_markup=back_to_main_kb())
