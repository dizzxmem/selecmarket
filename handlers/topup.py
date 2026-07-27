"""Хендлер пополнения баланса через CryptoBot (Crypto Pay)."""
import uuid
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import config
from keyboards import topup_amounts_kb, pay_url_kb, back_to_main_kb
from utils.cryptobot import create_invoice, get_invoice
from utils.photo import send_banner, edit_banner

router = Router()
logger = logging.getLogger(__name__)


class TopupStates(StatesGroup):
    waiting_amount  = State()
    waiting_payment = State()


# ─── Вход в пополнение ──────────────────────────────────────────────────────

def _topup_text() -> str:
    pct = int(config.topup_commission * 100)
    return (
        f"<b>💎 Пополнение баланса</b>\n\n"
        f"Оплата криптовалютой через @CryptoBot\n"
        f"Поддерживаются: USDT, TON, BTC, ETH, LTC, BNB, TRX, USDC\n\n"
        f"Минимальная сумма: <b>{config.min_topup} ₽</b>\n"
        f"Максимальная сумма: <b>{config.max_topup} ₽</b>\n"
        f"Комиссия сервиса: <b>{pct}%</b>\n\n"
        f"Выберите сумму или введите свою:"
    )


@router.message(F.text == "💳 Пополнить баланс")
async def topup_from_menu(message: Message, state: FSMContext, db_user: dict):
    if not db_user.get("agreed_tos"):
        await message.answer("Сначала примите пользовательское соглашение: /start")
        return
    await state.clear()
    await send_banner(message, _topup_text(), reply_markup=topup_amounts_kb())


@router.callback_query(F.data == "topup_menu")
async def topup_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await edit_banner(call, _topup_text(), reply_markup=topup_amounts_kb())


# ─── Готовые суммы ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("topup_amount:"))
async def topup_amount_chosen(call: CallbackQuery, state: FSMContext):
    amount = float(call.data.split(":")[1])
    await _create_invoice_flow(call, state, amount)


# ─── Произвольная сумма ─────────────────────────────────────────────────────

@router.callback_query(F.data == "topup_custom")
async def topup_custom(call: CallbackQuery, state: FSMContext):
    await state.set_state(TopupStates.waiting_amount)
    await edit_banner(
        call,
        f"✏️ <b>Введите сумму пополнения</b>\n\n"
        f"От {config.min_topup} до {config.max_topup} ₽:",
    )


@router.message(TopupStates.waiting_amount)
async def topup_custom_amount(message: Message, state: FSMContext):
    text = message.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = float(text)
    except ValueError:
        await message.answer("❌ Введите корректную сумму числом, например: <b>500</b>", parse_mode="HTML")
        return

    if amount < config.min_topup:
        await message.answer(f"❌ Минимальная сумма: <b>{config.min_topup} ₽</b>", parse_mode="HTML")
        return
    if amount > config.max_topup:
        await message.answer(f"❌ Максимальная сумма: <b>{config.max_topup} ₽</b>", parse_mode="HTML")
        return

    await _create_invoice_flow(message, state, amount)


# ─── Создание инвойса CryptoBot ─────────────────────────────────────────────

async def _create_invoice_flow(target, state: FSMContext, amount: float):
    user_id  = target.from_user.id
    order_id = f"tg_{user_id}_{uuid.uuid4().hex[:12]}"

    # Сумма с комиссией — это то, что платит пользователь
    commission     = config.topup_commission
    amount_to_pay  = round(amount * (1 + commission), 2)
    commission_rub = round(amount_to_pay - amount, 2)
    pct            = int(commission * 100)

    # В БД сохраняем оригинальную сумму (без комиссии) — столько зачислим на баланс
    await db.create_payment_record(user_id, order_id, amount)
    # Инвойс выставляем на сумму С комиссией
    result = await create_invoice(amount_to_pay, order_id, user_id)

    if not result or not result.get("bot_invoice_url"):
        err = (
            "❌ <b>Не удалось создать счёт.</b>\n\n"
            "Повторите попытку позже или обратитесь в поддержку."
        )
        if isinstance(target, CallbackQuery):
            await edit_banner(target, err, reply_markup=back_to_main_kb())
        else:
            await send_banner(target, err, reply_markup=back_to_main_kb())
        await db.update_payment_status(order_id, "error")
        return

    invoice_url = result["bot_invoice_url"]
    invoice_id  = str(result.get("invoice_id", ""))
    await db.update_payment_status(order_id, "created", invoice_id)
    await state.update_data(order_id=order_id, invoice_id=invoice_id, amount=amount)
    await state.set_state(TopupStates.waiting_payment)

    text = (
        f"<b>💎 Счёт создан</b>\n\n"
        f"Сумма пополнения: <b>{amount:.2f} ₽</b>\n"
        f"Комиссия {pct}%: <b>{commission_rub:.2f} ₽</b>\n"
        f"Итого к оплате: <b>{amount_to_pay:.2f} ₽</b>\n\n"
        f"Номер: <code>{order_id}</code>\n\n"
        f"Нажмите кнопку ниже — откроется @CryptoBot.\n"
        f"Выберите любую криптовалюту и оплатите.\n\n"
        f"После оплаты нажмите «🔄 Проверить оплату».\n"
        f"⏱ Счёт действителен 30 минут."
    )

    if isinstance(target, CallbackQuery):
        await edit_banner(target, text, reply_markup=pay_url_kb(invoice_url))
    else:
        await send_banner(target, text, reply_markup=pay_url_kb(invoice_url))


# ─── Проверка оплаты ────────────────────────────────────────────────────────

@router.callback_query(F.data == "check_payment", TopupStates.waiting_payment)
async def check_payment(call: CallbackQuery, state: FSMContext):
    data       = await state.get_data()
    order_id   = data.get("order_id")
    invoice_id = data.get("invoice_id")
    amount     = data.get("amount", 0.0)

    if not order_id:
        await call.answer("❌ Платёж не найден.", show_alert=True)
        return

    # Сначала проверяем свою БД (мог прийти вебхук)
    payment_record = await db.get_payment_by_order(order_id)
    if payment_record and payment_record["status"] == "paid":
        await call.answer("✅ Оплата уже зачислена!", show_alert=True)
        await state.clear()
        user = await db.get_user(call.from_user.id)
        await edit_banner(
            call,
            f"✅ <b>Баланс успешно пополнен!</b>\n\n"
            f"Зачислено: <b>+{amount:.2f} ₽</b>\n"
            f"Текущий баланс: <b>{user['balance']:.2f} ₽</b>",
            reply_markup=back_to_main_kb(),
        )
        return

    # Запрашиваем статус напрямую у CryptoBot
    if invoice_id:
        invoice = await get_invoice(int(invoice_id))
        if invoice and invoice.get("status") == "paid":
            await _credit_balance(call, state, order_id, invoice_id, amount)
            return

    await call.answer(
        "⏳ Оплата ещё не поступила. Попробуйте через несколько секунд.",
        show_alert=True
    )


async def _credit_balance(
    call: CallbackQuery,
    state: FSMContext,
    order_id: str,
    invoice_id: str,
    amount: float,
):
    await db.update_payment_status(order_id, "paid", invoice_id)
    new_balance = await db.update_balance(call.from_user.id, amount)
    await db.add_log(call.from_user.id, "topup", f"+{amount:.2f} ₽ via CryptoBot, order={order_id}")
    await state.clear()
    await edit_banner(
        call,
        f"✅ <b>Баланс успешно пополнен!</b>\n\n"
        f"Зачислено: <b>+{amount:.2f} ₽</b>\n"
        f"Текущий баланс: <b>{new_balance:.2f} ₽</b>",
        reply_markup=back_to_main_kb(),
    )


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(call: CallbackQuery, state: FSMContext):
    data     = await state.get_data()
    order_id = data.get("order_id")
    if order_id:
        await db.update_payment_status(order_id, "canceled")
    await state.clear()
    await edit_banner(
        call,
        "❌ <b>Платёж отменён.</b>",
        reply_markup=back_to_main_kb(),
    )
