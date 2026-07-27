"""Хендлер поддержки."""
from aiogram import Router, F
from aiogram.types import Message

from config import config
from keyboards import back_to_main_kb
from utils.photo import send_banner

router = Router()


@router.message(F.text == "📞 Поддержка")
async def support_handler(message: Message, db_user: dict):
    if not db_user.get("agreed_tos"):
        await message.answer("Сначала примите пользовательское соглашение: /start")
        return

    support = config.support_username
    if not support.startswith("@"):
        support = f"@{support}"

    text = (
        f"<b>📞 Поддержка Selectel Market</b>\n\n"
        f"Столкнулись с проблемой или есть вопросы? Мы всегда готовы помочь!\n\n"
        f"👤 Написать в поддержку: {support}\n\n"
        f"<b>Часто задаваемые вопросы:</b>\n\n"
        f"❓ <i>Как купить аккаунт?</i>\n"
        f"Перейдите в раздел «📦 Купить аккаунты», выберите аккаунт и следуйте инструкциям.\n\n"
        f"❓ <i>Как пополнить баланс?</i>\n"
        f"Нажмите «💳 Пополнить баланс». Оплата через СБП.\n\n"
        f"❓ <i>Аккаунт не работает?</i>\n"
        f"Обратитесь в поддержку в течение 30 минут после покупки со скриншотом.\n\n"
        f"⏱ Время ответа: обычно до 30 минут."
    )

    await send_banner(message, text, reply_markup=back_to_main_kb())
