"""Хендлер администратора: аккаунты, рассылка, пользователи, статистика."""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter

import database as db
from config import config
from keyboards import (
    admin_main_kb, admin_accounts_list_kb, admin_account_detail_kb,
    admin_users_list_kb, admin_user_detail_kb, admin_confirm_delete_kb,
    back_to_main_kb,
)

router = Router()
logger = logging.getLogger(__name__)


# ─── Фильтр: только для администраторов ────────────────────────────────────

class IsAdmin(Filter):
    async def __call__(self, event) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and config.is_admin(user.id)


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ─── FSM ────────────────────────────────────────────────────────────────────

class AdminStates(StatesGroup):
    # Загрузка нового аккаунта (пошагово)
    upload_title      = State()
    upload_desc       = State()
    upload_price      = State()
    upload_email_pass = State()  # "логин:пароль" от почты
    upload_acc_number = State()
    upload_acc_pass   = State()
    upload_note       = State()
    # Рассылка
    broadcast_text    = State()
    # Редактирование
    edit_acc_title    = State()
    edit_acc_desc     = State()
    edit_acc_price    = State()
    edit_acc_email_pass = State()
    edit_acc_number   = State()
    edit_acc_pass     = State()
    edit_acc_note     = State()


# ─── Вход в панель ──────────────────────────────────────────────────────────

@router.message(F.text == "🔴 Администрирование")
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>🔴 Панель администратора</b>\n\nВыберите действие:",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "<b>🔴 Панель администратора</b>\n\nВыберите действие:",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_exit")
async def admin_exit(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer("Выход из панели администратора.")


# ─── Загрузка аккаунта (пошаговый FSM) ─────────────────────────────────────

def _cancel_hint() -> str:
    return "\n\n<i>Отправьте /cancel чтобы отменить.</i>"


async def _check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("❌ Добавление отменено.", reply_markup=admin_main_kb())
        return True
    return False


@router.callback_query(F.data == "admin_upload_accs")
async def admin_upload_accs_start(call: CallbackQuery, state: FSMContext):
    accounts = await db.get_all_accounts()
    if accounts:
        await call.message.edit_text(
            f"<b>📚 Аккаунты в базе</b> (всего: {len(accounts)})\n\n"
            "Выберите аккаунт для управления или добавьте новый:",
            reply_markup=admin_accounts_list_kb(accounts),
            parse_mode="HTML"
        )
    else:
        await _start_upload_flow(call.message, state, edit=True)


@router.callback_query(F.data == "admin_upload_accs_form")
async def admin_upload_form(call: CallbackQuery, state: FSMContext):
    await _start_upload_flow(call.message, state, edit=True)


async def _start_upload_flow(msg, state: FSMContext, edit: bool = False):
    await state.set_state(AdminStates.upload_title)
    text = (
        "<b>📚 Добавление аккаунта — шаг 1/7</b>\n\n"
        "Введите <b>название аккаунта</b>:\n"
        "<i>Например: Selectel Standard</i>"
        + _cancel_hint()
    )
    if edit:
        await msg.edit_text(text, parse_mode="HTML")
    else:
        await msg.answer(text, parse_mode="HTML")


# Шаг 1 — Название
@router.message(AdminStates.upload_title)
async def upload_step_title(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminStates.upload_desc)
    await message.answer(
        "<b>Шаг 2/7</b> — Введите <b>описание</b> аккаунта:\n"
        "<i>Например: Верифицирован, 500 бонусов. Или «-» чтобы пропустить.</i>"
        + _cancel_hint(),
        parse_mode="HTML"
    )


# Шаг 2 — Описание
@router.message(AdminStates.upload_desc)
async def upload_step_desc(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    raw = message.text.strip()
    await state.update_data(description="" if raw == "-" else raw)
    await state.set_state(AdminStates.upload_price)
    await message.answer(
        "<b>Шаг 3/7</b> — Введите <b>цену</b> аккаунта в рублях:\n"
        "<i>Например: 500</i>"
        + _cancel_hint(),
        parse_mode="HTML"
    )


# Шаг 3 — Цена
@router.message(AdminStates.upload_price)
async def upload_step_price(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    raw = message.text.strip().replace(",", ".")
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную сумму, например: <b>500</b>", parse_mode="HTML")
        return
    await state.update_data(price=price)
    await state.set_state(AdminStates.upload_email_pass)
    await message.answer(
        "<b>Шаг 4/7</b> — Отправьте <b>почту и пароль</b> от почты в формате:\n\n"
        "<code>почта:пароль</code>\n\n"
        "<i>Например: user@mail.ru:mypassword123</i>"
        + _cancel_hint(),
        parse_mode="HTML"
    )


# Шаг 4 — Почта:пароль
@router.message(AdminStates.upload_email_pass)
async def upload_step_email_pass(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    raw = message.text.strip()
    if ":" not in raw:
        await message.answer(
            "❌ Неверный формат. Нужно: <code>почта:пароль</code>",
            parse_mode="HTML"
        )
        return
    email, _, email_pass = raw.partition(":")
    email = email.strip()
    email_pass = email_pass.strip()
    if not email or not email_pass:
        await message.answer(
            "❌ Почта или пароль не могут быть пустыми.",
            parse_mode="HTML"
        )
        return
    await state.update_data(email=email, email_pass=email_pass)
    await state.set_state(AdminStates.upload_acc_number)
    await message.answer(
        "<b>Шаг 5/7</b> — Введите <b>номер аккаунта</b> Selectel:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


# Шаг 5 — Номер аккаунта
@router.message(AdminStates.upload_acc_number)
async def upload_step_acc_number(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    await state.update_data(acc_number=message.text.strip())
    await state.set_state(AdminStates.upload_acc_pass)
    await message.answer(
        "<b>Шаг 6/7</b> — Введите <b>пароль от аккаунта</b> Selectel:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


# Шаг 6 — Пароль от аккаунта
@router.message(AdminStates.upload_acc_pass)
async def upload_step_acc_pass(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    await state.update_data(acc_pass=message.text.strip())
    await state.set_state(AdminStates.upload_note)
    await message.answer(
        "<b>Шаг 7/7</b> — Введите <b>примечание</b> по аккаунту:\n"
        "<i>Отправьте «-» чтобы оставить пустым.</i>"
        + _cancel_hint(),
        parse_mode="HTML"
    )


# Шаг 7 — Примечание → сохраняем
@router.message(AdminStates.upload_note)
async def upload_step_note(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    raw = message.text.strip()
    data = await state.get_data()
    data["note"] = "" if raw == "-" else raw

    acc_id = await db.add_account(data)
    await db.add_log(message.from_user.id, "admin_upload", f"Добавлен аккаунт #{acc_id} «{data['title']}»")
    await state.clear()

    await message.answer(
        f"✅ <b>Аккаунт добавлен!</b>\n\n"
        f"📌 Название: {data['title']}\n"
        f"💰 Цена: {data['price']:.2f} ₽\n"
        f"📧 Почта: {data['email']}\n"
        f"🔑 Номер аккаунта: {data['acc_number']}\n\n"
        f"Хотите добавить ещё один?",
        reply_markup=_add_another_kb(),
        parse_mode="HTML"
    )


def _add_another_kb():
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить ещё", callback_data="admin_upload_accs_form")
    builder.button(text="📚 К списку",     callback_data="admin_upload_accs")
    builder.button(text="◀️ В меню",       callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


# ─── Просмотр / редактирование / удаление аккаунта ─────────────────────────

@router.callback_query(F.data.startswith("admin_acc:"))
async def admin_acc_detail(call: CallbackQuery):
    account_id = int(call.data.split(":")[1])
    acc = await db.get_account(account_id)
    if not acc:
        await call.answer("Аккаунт не найден.", show_alert=True)
        return

    status = "✅ Доступен" if not acc["is_sold"] else f"❌ Продан (user #{acc['sold_to']})"
    note_line = f"\n📝 Примечание: {acc['note']}" if acc.get("note") else ""
    text = (
        f"<b>💻 Аккаунт #{acc['id']}</b>\n\n"
        f"📌 Название: {acc['title']}\n"
        f"📋 Описание: {acc.get('description') or '—'}\n"
        f"💰 Цена: {acc['price']:.2f} ₽\n\n"
        f"📧 Почта: <code>{acc['email']}</code>\n"
        f"🔑 Пароль почты: <code>{acc['email_pass']}</code>\n\n"
        f"🆔 Номер аккаунта: <code>{acc['acc_number']}</code>\n"
        f"🔐 Пароль аккаунта: <code>{acc['acc_pass']}</code>"
        f"{note_line}\n\n"
        f"📊 Статус: {status}\n"
        f"📅 Создан: {acc['created_at'][:10]}"
    )
    await call.message.edit_text(
        text,
        reply_markup=admin_account_detail_kb(account_id),
        parse_mode="HTML"
    )


def _keep(new_val: str, old_val: str) -> str:
    """Если пользователь отправил «.» — оставляем старое значение."""
    return old_val if new_val.strip() == "." else new_val.strip()


@router.callback_query(F.data.startswith("admin_edit_acc:"))
async def admin_edit_acc_start(call: CallbackQuery, state: FSMContext):
    account_id = int(call.data.split(":")[1])
    acc = await db.get_account(account_id)
    if not acc:
        await call.answer("Аккаунт не найден.", show_alert=True)
        return
    await state.update_data(editing_acc_id=account_id)
    await state.set_state(AdminStates.edit_acc_title)
    await call.message.edit_text(
        f"✏️ <b>Редактирование аккаунта #{account_id}</b>\n\n"
        f"Текущее название: <b>{acc['title']}</b>\n\n"
        f"Введите новое название или «.» чтобы оставить:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


@router.message(AdminStates.edit_acc_title)
async def admin_edit_acc_title(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    data = await state.get_data()
    acc = await db.get_account(data["editing_acc_id"])
    await state.update_data(new_title=_keep(message.text, acc["title"]))
    await state.set_state(AdminStates.edit_acc_desc)
    await message.answer(
        f"Текущее описание: <b>{acc.get('description') or '—'}</b>\n\n"
        f"Введите новое описание или «.» чтобы оставить. «-» для пустого:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


@router.message(AdminStates.edit_acc_desc)
async def admin_edit_acc_desc(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    data = await state.get_data()
    acc = await db.get_account(data["editing_acc_id"])
    raw = message.text.strip()
    if raw == ".":
        new_desc = acc.get("description") or ""
    elif raw == "-":
        new_desc = ""
    else:
        new_desc = raw
    await state.update_data(new_desc=new_desc)
    await state.set_state(AdminStates.edit_acc_price)
    await message.answer(
        f"Текущая цена: <b>{acc['price']:.2f} ₽</b>\n\n"
        f"Введите новую цену или «.» чтобы оставить:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


@router.message(AdminStates.edit_acc_price)
async def admin_edit_acc_price(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    data = await state.get_data()
    acc = await db.get_account(data["editing_acc_id"])
    raw = message.text.strip()
    if raw == ".":
        new_price = acc["price"]
    else:
        try:
            new_price = float(raw.replace(",", "."))
            if new_price <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Некорректная цена. Попробуйте снова:")
            return
    await state.update_data(new_price=new_price)
    await state.set_state(AdminStates.edit_acc_email_pass)
    await message.answer(
        f"Текущая почта: <code>{acc['email']}</code>\n"
        f"Текущий пароль почты: <code>{acc['email_pass']}</code>\n\n"
        f"Отправьте <code>почта:пароль</code> или «.» чтобы оставить:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


@router.message(AdminStates.edit_acc_email_pass)
async def admin_edit_acc_email_pass(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    data = await state.get_data()
    acc = await db.get_account(data["editing_acc_id"])
    raw = message.text.strip()
    if raw == ".":
        await state.update_data(new_email=acc["email"], new_email_pass=acc["email_pass"])
    else:
        if ":" not in raw:
            await message.answer("❌ Формат: <code>почта:пароль</code>", parse_mode="HTML")
            return
        email, _, email_pass = raw.partition(":")
        await state.update_data(new_email=email.strip(), new_email_pass=email_pass.strip())
    await state.set_state(AdminStates.edit_acc_number)
    await message.answer(
        f"Текущий номер аккаунта: <code>{acc['acc_number']}</code>\n\n"
        f"Введите новый или «.» чтобы оставить:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


@router.message(AdminStates.edit_acc_number)
async def admin_edit_acc_number(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    data = await state.get_data()
    acc = await db.get_account(data["editing_acc_id"])
    await state.update_data(new_acc_number=_keep(message.text, acc["acc_number"]))
    await state.set_state(AdminStates.edit_acc_pass)
    await message.answer(
        f"Текущий пароль аккаунта: <code>{acc['acc_pass']}</code>\n\n"
        f"Введите новый или «.» чтобы оставить:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


@router.message(AdminStates.edit_acc_pass)
async def admin_edit_acc_pass(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    data = await state.get_data()
    acc = await db.get_account(data["editing_acc_id"])
    await state.update_data(new_acc_pass=_keep(message.text, acc["acc_pass"]))
    await state.set_state(AdminStates.edit_acc_note)
    current_note = acc.get("note") or "—"
    await message.answer(
        f"Текущее примечание: <b>{current_note}</b>\n\n"
        f"Введите новое, «-» для пустого или «.» чтобы оставить:"
        + _cancel_hint(),
        parse_mode="HTML"
    )


@router.message(AdminStates.edit_acc_note)
async def admin_edit_acc_note(message: Message, state: FSMContext):
    if await _check_cancel(message, state):
        return
    data = await state.get_data()
    acc = await db.get_account(data["editing_acc_id"])
    raw = message.text.strip()
    if raw == ".":
        new_note = acc.get("note") or ""
    elif raw == "-":
        new_note = ""
    else:
        new_note = raw

    await db.update_account(
        data["editing_acc_id"],
        data["new_title"],
        data["new_desc"],
        data["new_price"],
        data["new_email"],
        data["new_email_pass"],
        data["new_acc_number"],
        data["new_acc_pass"],
        new_note,
    )
    await db.add_log(message.from_user.id, "admin_edit_acc", f"Изменён аккаунт #{data['editing_acc_id']}")
    await state.clear()
    await message.answer(
        "✅ <b>Аккаунт обновлён.</b>",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_del_acc:"))
async def admin_del_acc_confirm(call: CallbackQuery):
    account_id = int(call.data.split(":")[1])
    acc = await db.get_account(account_id)
    if not acc:
        await call.answer("Аккаунт не найден.", show_alert=True)
        return
    await call.message.edit_text(
        f"⚠️ <b>Удалить аккаунт #{account_id} «{acc['title']}»?</b>\n\nДействие необратимо.",
        reply_markup=admin_confirm_delete_kb(account_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_del_confirm:"))
async def admin_del_acc_do(call: CallbackQuery):
    account_id = int(call.data.split(":")[1])
    await db.delete_account(account_id)
    await db.add_log(call.from_user.id, "admin_del_acc", f"Удалён аккаунт #{account_id}")
    await call.message.edit_text(
        "✅ <b>Аккаунт удалён.</b>",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


# ─── Рассылка ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.broadcast_text)
    await call.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение для рассылки всем пользователям.\n"
        "Поддерживается HTML-разметка.\n\n"
        "Отправьте /cancel чтобы отменить.",
        parse_mode="HTML"
    )


@router.message(AdminStates.broadcast_text)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_main_kb())
        return

    await state.clear()
    users = await db.get_all_users()
    sent = 0
    failed = 0

    status_msg = await message.answer(f"⏳ Отправка... 0/{len(users)}")

    for user in users:
        try:
            await bot.send_message(
                user["id"],
                message.text or "",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1

        if (sent + failed) % 10 == 0:
            try:
                await status_msg.edit_text(f"⏳ Отправка... {sent + failed}/{len(users)}")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {failed}",
        parse_mode="HTML"
    )
    await db.add_log(message.from_user.id, "admin_broadcast", f"sent={sent}, failed={failed}")


# ─── Пользователи ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    users = await db.get_all_users()
    if not users:
        await call.message.edit_text(
            "👥 Пользователей пока нет.",
            reply_markup=admin_main_kb(),
            parse_mode="HTML"
        )
        return
    await call.message.edit_text(
        f"<b>👥 Пользователи</b> (всего: {len(users)})\n\nВыберите пользователя:",
        reply_markup=admin_users_list_kb(users, page=0),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_users_page:"))
async def admin_users_page(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    users = await db.get_all_users()
    await call.message.edit_text(
        f"<b>👥 Пользователи</b> (всего: {len(users)})\n\nВыберите пользователя:",
        reply_markup=admin_users_list_kb(users, page=page),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_user:"))
async def admin_user_detail(call: CallbackQuery):
    user_id = int(call.data.split(":")[1])
    user = await db.get_user(user_id)
    if not user:
        await call.answer("Пользователь не найден.", show_alert=True)
        return
    last_order = await db.get_last_order(user_id)

    username = f"@{user['username']}" if user.get("username") else "нет"
    last_purchase = "—"
    if last_order:
        last_purchase = f"{last_order.get('title', '?')} ({last_order.get('created_at', '')[:10]})"

    import aiosqlite
    from config import config as _cfg
    async with aiosqlite.connect(_cfg.db_path) as _db:
        _db.row_factory = aiosqlite.Row
        cur = await _db.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(amount),0) as total FROM orders WHERE user_id=?",
            (user_id,)
        )
        stats = await cur.fetchone()

    text = (
        f"<b>👤 Пользователь #{user_id}</b>\n\n"
        f"👥 Username: {username}\n"
        f"📛 Имя: {user.get('full_name', '—')}\n"
        f"💳 Баланс: <b>{user['balance']:.2f} ₽</b>\n"
        f"🗳 Покупок: {stats['cnt']}  |  На сумму: {stats['total']:.2f} ₽\n"
        f"📅 Регистрация: {user['created_at'][:10]}\n"
        f"🕐 Последняя активность: {user['last_seen'][:16]}\n"
        f"📦 Последняя покупка: {last_purchase}\n"
        f"🚫 Бан: {'Да' if user.get('is_banned') else 'Нет'}"
    )
    await call.message.edit_text(
        text,
        reply_markup=admin_user_detail_kb(user_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_user_logs:"))
async def admin_user_logs(call: CallbackQuery):
    user_id = int(call.data.split(":")[1])
    logs = await db.get_user_logs(user_id, limit=15)
    if not logs:
        await call.answer("Логов нет.", show_alert=True)
        return

    lines = [f"<b>📜 Логи пользователя #{user_id} (последние 15):</b>\n"]
    for log in logs:
        lines.append(
            f"• <b>{log['action']}</b>  <i>{log['created_at'][:16]}</i>\n"
            f"  {log.get('details', '')}"
        )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=f"admin_user:{user_id}")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


# ─── Статистика ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    import aiosqlite
    from config import config as _cfg

    async with aiosqlite.connect(_cfg.db_path) as _db:
        _db.row_factory = aiosqlite.Row

        r = await (await _db.execute("SELECT COUNT(*) as cnt FROM users")).fetchone()
        total_users = r["cnt"]

        r = await (await _db.execute("SELECT COUNT(*) as cnt FROM accounts WHERE is_sold=0")).fetchone()
        avail_accs = r["cnt"]

        r = await (await _db.execute("SELECT COUNT(*) as cnt FROM accounts WHERE is_sold=1")).fetchone()
        sold_accs = r["cnt"]

        r = await (await _db.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM orders"
        )).fetchone()
        total_revenue = r["total"]

        r = await (await _db.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM payments WHERE status='paid'"
        )).fetchone()
        total_topups = r["total"]

        r = await (await _db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE date(created_at)=date('now')"
        )).fetchone()
        new_today = r["cnt"]

    await call.message.edit_text(
        f"<b>📈 Статистика Selectel Market</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"👤 Новых сегодня: <b>{new_today}</b>\n\n"
        f"📦 Аккаунтов доступно: <b>{avail_accs}</b>\n"
        f"✅ Продано аккаунтов: <b>{sold_accs}</b>\n\n"
        f"💰 Выручка (покупки): <b>{total_revenue:.2f} ₽</b>\n"
        f"💳 Пополнений: <b>{total_topups:.2f} ₽</b>",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )
