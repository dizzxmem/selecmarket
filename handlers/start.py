"""Хендлер /start и главное меню."""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

import database as db
from config import config
from keyboards import main_menu_kb, main_menu_admin_kb, tos_kb
from utils.photo import send_banner, edit_banner

router = Router()

TOS_TEXT = (
    "<b>📋 Пользовательское соглашение Selectel Market</b>\n\n"
    "Перед началом работы вы обязаны принять настоящее Соглашение.\n\n"
    "<b>1. Предмет</b>\n"
    "Selectel Market — маркетплейс цифровых аккаунтов. Все продажи финальны.\n\n"
    "<b>2. Отказ от ответственности</b>\n"
    "• После выдачи данных Продавец <b>не несёт ответственности</b> за блокировку, смену данных или ограничение функций.\n"
    "• Товар продаётся «как есть». Возврат после раскрытия данных невозможен.\n"
    "• Продавец не аффилирован с Selectel.\n\n"
    "<b>3. Обязанности покупателя</b>\n"
    "• Использовать аккаунты законно, по правилам Selectel.\n"
    "• Не использовать в мошеннических целях.\n\n"
    "<b>4. Данные и возраст</b>\n"
    "Бот хранит только Telegram ID и историю транзакций. Используя бота, вы подтверждаете, что вам <b>18+ лет</b>.\n\n"
    "Нажимая «✅ Принимаю», вы соглашаетесь с условиями."
)

WELCOME_TEXT = (
    "<b>☀️ Добро пожаловать в Selectel Market!</b>\n\n"
    "Здесь вы можете приобрести аккаунты <b>Selectel</b> — ведущего российского облачного провайдера.\n\n"
    "<b>💻 Преимущества:</b>\n"
    "• Проверенные аккаунты\n"
    "• Моментальная автовыдача после оплаты\n"
    "• Безопасная оплата через СБП\n"
    "• Поддержка 24/7\n\n"
    "Выберите действие в меню ниже 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: dict):
    if not db_user.get("agreed_tos"):
        await send_banner(message, TOS_TEXT, reply_markup=tos_kb())
        return

    kb = main_menu_admin_kb() if config.is_admin(message.from_user.id) else main_menu_kb()
    await send_banner(message, WELCOME_TEXT, reply_markup=kb)
    await db.add_log(message.from_user.id, "start", "Открыл бота")


@router.callback_query(F.data == "tos_accept")
async def tos_accept(call: CallbackQuery, db_user: dict):
    await db.set_agreed_tos(call.from_user.id)
    await db.add_log(call.from_user.id, "tos_accept", "Принял соглашение")
    await edit_banner(call, "✅ <b>Спасибо! Условия приняты.</b>")
    kb = main_menu_admin_kb() if config.is_admin(call.from_user.id) else main_menu_kb()
    await send_banner(call.message, WELCOME_TEXT, reply_markup=kb)


@router.callback_query(F.data == "tos_decline")
async def tos_decline(call: CallbackQuery):
    await edit_banner(
        call,
        "❌ Вы отклонили соглашение.\n\nДля использования бота необходимо его принять.\n\n"
        "Отправьте /start чтобы попробовать снова.",
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(call: CallbackQuery):
    kb = main_menu_admin_kb() if config.is_admin(call.from_user.id) else main_menu_kb()
    await edit_banner(call, WELCOME_TEXT, reply_markup=kb)
