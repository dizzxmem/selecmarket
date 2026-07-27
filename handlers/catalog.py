"""Хендлер каталога аккаунтов."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import (
    accounts_list_kb, account_detail_kb,
    confirm_buy_kb, back_to_main_kb
)
from utils.photo import send_banner, edit_banner

router = Router()


@router.message(F.text == "📦 Купить аккаунты")
async def catalog_handler(message: Message, db_user: dict):
    if not db_user.get("agreed_tos"):
        await message.answer("Сначала примите пользовательское соглашение: /start")
        return

    accounts = await db.get_available_accounts()
    if not accounts:
        await send_banner(
            message,
            "📭 <b>Аккаунтов пока нет.</b>\n\nЗагляните позже — скоро появятся новые!",
            reply_markup=back_to_main_kb(),
        )
        return

    await send_banner(
        message,
        f"<b>📦 Каталог аккаунтов Selectel</b>\n\n"
        f"Доступно: <b>{len(accounts)}</b> аккаунт(ов)\n\n"
        f"Выберите аккаунт для покупки 👇",
        reply_markup=accounts_list_kb(accounts),
    )


@router.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(call: CallbackQuery, db_user: dict):
    accounts = await db.get_available_accounts()
    if not accounts:
        await edit_banner(
            call,
            "📭 <b>Аккаунтов пока нет.</b>",
            reply_markup=back_to_main_kb(),
        )
        return

    await edit_banner(
        call,
        f"<b>📦 Каталог аккаунтов Selectel</b>\n\n"
        f"Доступно: <b>{len(accounts)}</b> аккаунт(ов)\n\n"
        f"Выберите аккаунт для покупки 👇",
        reply_markup=accounts_list_kb(accounts),
    )


@router.callback_query(F.data.startswith("buy_acc:"))
async def account_detail(call: CallbackQuery, db_user: dict):
    account_id = int(call.data.split(":")[1])
    acc = await db.get_account(account_id)
    if not acc or acc["is_sold"]:
        await call.answer("❌ Этот аккаунт уже продан или недоступен.", show_alert=True)
        return

    user = await db.get_user(call.from_user.id)
    balance = user.get("balance", 0.0)
    can_afford = balance >= acc["price"]

    desc = acc.get("description") or "Описание отсутствует."
    diff = acc["price"] - balance

    text = (
        f"<b>💻 {acc['title']}</b>\n\n"
        f"📝 {desc}\n\n"
        f"💰 Цена: <b>{acc['price']:.2f} ₽</b>\n"
        f"💳 Ваш баланс: <b>{balance:.2f} ₽</b>\n"
    )
    if not can_afford:
        text += f"\n❌ Недостаточно средств. Нужно пополнить: <b>+{diff:.2f} ₽</b>"
    else:
        text += "\n✅ У вас достаточно средств для покупки."

    await edit_banner(call, text, reply_markup=account_detail_kb(account_id, can_afford))


@router.callback_query(F.data.startswith("confirm_buy:"))
async def confirm_buy(call: CallbackQuery, db_user: dict):
    account_id = int(call.data.split(":")[1])
    acc = await db.get_account(account_id)
    if not acc or acc["is_sold"]:
        await call.answer("❌ Аккаунт уже продан.", show_alert=True)
        return

    user = await db.get_user(call.from_user.id)
    if user["balance"] < acc["price"]:
        await call.answer("❌ Недостаточно средств.", show_alert=True)
        return

    await edit_banner(
        call,
        f"<b>⚠️ Подтверждение покупки</b>\n\n"
        f"💻 Аккаунт: <b>{acc['title']}</b>\n"
        f"💰 Сумма: <b>{acc['price']:.2f} ₽</b>\n\n"
        f"После подтверждения данные аккаунта будут выданы автоматически.\n"
        f"<i>Возврат средств после раскрытия данных невозможен.</i>",
        reply_markup=confirm_buy_kb(account_id),
    )


@router.callback_query(F.data.startswith("do_buy:"))
async def do_buy(call: CallbackQuery, db_user: dict):
    account_id = int(call.data.split(":")[1])

    # Повторная проверка (защита от race condition)
    acc = await db.get_account(account_id)
    if not acc or acc["is_sold"]:
        await call.answer("❌ Аккаунт уже был куплен другим пользователем.", show_alert=True)
        return

    user = await db.get_user(call.from_user.id)
    if user["balance"] < acc["price"]:
        await call.answer("❌ Недостаточно средств.", show_alert=True)
        return

    # Списываем баланс, помечаем аккаунт проданным
    await db.update_balance(call.from_user.id, -acc["price"])
    await db.sell_account(account_id, call.from_user.id)
    await db.create_order(call.from_user.id, account_id, acc["price"])
    await db.add_log(
        call.from_user.id,
        "purchase",
        f"Куплен аккаунт #{account_id} «{acc['title']}» за {acc['price']:.2f} ₽"
    )

    user_after = await db.get_user(call.from_user.id)

    note_line = f"\n📝 <b>Примечание:</b> {acc['note']}" if acc.get("note") else ""

    await edit_banner(
        call,
        f"✅ <b>Ваш аккаунт готов!</b>\n\n"
        f"<b>Данные от почты:</b>\n"
        f"📧 Почта: <code>{acc['email']}</code>\n"
        f"🔑 Пароль: <code>{acc['email_pass']}</code>\n\n"
        f"<b>Данные от аккаунта:</b>\n"
        f"🆔 Номер аккаунта: <code>{acc['acc_number']}</code>\n"
        f"🔐 Пароль от аккаунта: <code>{acc['acc_pass']}</code>"
        f"{note_line}\n\n"
        f"💳 Остаток на балансе: <b>{user_after['balance']:.2f} ₽</b>\n\n"
        f"<i>Нажмите на текст чтобы скопировать. Сохраните данные — повторный доступ невозможен.</i>",
        reply_markup=back_to_main_kb(),
    )
