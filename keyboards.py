"""Клавиатуры бота Selectel Market с премиум-эмодзи."""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict, Any

# ────────────────────────────────────────────────────────────
#  Премиум кастомные эмодзи (custom_emoji_id)
# ────────────────────────────────────────────────────────────
EMOJI = {
    "cart":      ("🛒", "5258134813302332906"),   # 📦
    "profile":   ("👤", "5258486128742244085"),   # 👥
    "support":   ("💬", "5258020476977946656"),   # 📞
    "topup":     ("💳", "5260412365739925015"),   # ⭐️
    "back":      ("◀️", "5258132936401624790"),   # ⬅️
    "ok":        ("✅", "5260416304224936047"),
    "error":     ("❌", "5258453452631056344"),
    "info":      ("ℹ️", "5258503720928288433"),
    "arrow":     ("➡️", "5258215850745275216"),
    "star":      ("⭐️", "5260412365739925015"),
    "fire":      ("☀️", "5258089153505009279"),
    "refresh":   ("🔄", "5258420634785947640"),
    "up":        ("⬆️", "5258043150110301407"),
    "down":      ("⬇️", "5258336354642697821"),
    "admin":     ("🔫", "5260221883940347555"),
    "users":     ("👥", "5258486128742244085"),
    "broadcast": ("📢", "5258391025281408576"),   # 📈
    "accounts":  ("📚", "5260512129240276089"),
    "clock":     ("🕐", "5258419835922030550"),
    "eye":       ("👀", "5260341314095947411"),
    "computer":  ("💻", "5258423306255604960"),
    "chart":     ("📈", "5258391025281408576"),
    "hand":      ("✋", "5258362429389152256"),
    "orders":    ("🗳", "5258200019495821936"),
    "pic":       ("🖼", "5258254475386167466"),
    "wave":      ("🤚", "5260249440450520061"),
    "smile":     ("🙂", "5258262708838472996"),
    "plane":     ("✈️", "5258073068852485953"),
}


def _ce(key: str) -> str:
    """Возвращает строку с кастомным эмодзи для текста сообщения."""
    symbol, cid = EMOJI[key]
    return f'<tg-emoji emoji-id="{cid}">{symbol}</tg-emoji>'


def _btn_ce(key: str) -> str:
    """Возвращает текст кнопки с кастомным эмодзи (plain-текст + unicode-запасной)."""
    symbol, _ = EMOJI[key]
    return symbol  # В кнопках tg-emoji не рендерится, используем unicode-символы


# ────────────────────────────────────────────────────────────
#  Главное меню
# ────────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Купить аккаунты")
    builder.button(text="👤 Профиль")
    builder.button(text="📞 Поддержка")
    builder.button(text="💳 Пополнить баланс")
    builder.adjust(2, 2)
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел..."
    )


def main_menu_admin_kb() -> ReplyKeyboardMarkup:
    """Главное меню с кнопкой администратора."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Купить аккаунты")
    builder.button(text="👤 Профиль")
    builder.button(text="📞 Поддержка")
    builder.button(text="💳 Пополнить баланс")
    builder.button(text="🔴 Администрирование")
    builder.adjust(2, 2, 1)
    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел..."
    )


# ────────────────────────────────────────────────────────────
#  Профиль
# ────────────────────────────────────────────────────────────

def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💳 Пополнить баланс",
        callback_data="topup_menu"
    )
    builder.button(
        text="🗳 История покупок",
        callback_data="my_orders"
    )
    builder.adjust(1)
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
#  Пополнение баланса
# ────────────────────────────────────────────────────────────

def topup_amounts_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    amounts = [100, 250, 500, 1000, 2500, 5000]
    for a in amounts:
        builder.button(text=f"⭐️ {a} ₽", callback_data=f"topup_amount:{a}")
    builder.button(text="✏️ Своя сумма", callback_data="topup_custom")
    builder.button(text="◀️ Назад", callback_data="back_to_profile")
    builder.adjust(3, 3, 1, 1)
    return builder.as_markup()


def pay_url_kb(url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 Оплатить через CryptoBot", url=url)
    builder.button(text="🔄 Проверить оплату", callback_data="check_payment")
    builder.button(text="❌ Отмена", callback_data="cancel_payment")
    builder.adjust(1)
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Главное меню", callback_data="back_to_main")
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
#  Пользовательское соглашение
# ────────────────────────────────────────────────────────────

def tos_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принимаю условия", callback_data="tos_accept")
    builder.button(text="❌ Не принимаю", callback_data="tos_decline")
    builder.adjust(1)
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
#  Каталог аккаунтов
# ────────────────────────────────────────────────────────────

def accounts_list_kb(accounts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for acc in accounts:
        label = f"💻 {acc['title']}  —  {acc['price']:.0f} ₽"
        builder.button(text=label, callback_data=f"buy_acc:{acc['id']}")
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def account_detail_kb(account_id: int, can_afford: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_afford:
        builder.button(text="✅ Купить", callback_data=f"confirm_buy:{account_id}")
    else:
        builder.button(text="💳 Пополнить баланс", callback_data="topup_menu")
    builder.button(text="◀️ Назад к списку", callback_data="back_to_catalog")
    builder.adjust(1)
    return builder.as_markup()


def confirm_buy_kb(account_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить покупку", callback_data=f"do_buy:{account_id}")
    builder.button(text="◀️ Отмена", callback_data="back_to_catalog")
    builder.adjust(1)
    return builder.as_markup()


# ────────────────────────────────────────────────────────────
#  Администрирование
# ────────────────────────────────────────────────────────────

def admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Загрузить аккаунты",  callback_data="admin_upload_accs")
    builder.button(text="📢 Рассылка",            callback_data="admin_broadcast")
    builder.button(text="👥 Пользователи",        callback_data="admin_users")
    builder.button(text="📈 Статистика",          callback_data="admin_stats")
    builder.button(text="◀️ Выйти",              callback_data="admin_exit")
    builder.adjust(1)
    return builder.as_markup()


def admin_accounts_list_kb(accounts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for acc in accounts:
        status = "✅" if not acc["is_sold"] else "❌"
        label = f"{status} {acc['title']}  —  {acc['price']:.0f} ₽"
        builder.button(text=label, callback_data=f"admin_acc:{acc['id']}")
    builder.button(text="➕ Добавить ещё", callback_data="admin_upload_accs")
    builder.button(text="◀️ Назад",        callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()


def admin_account_detail_kb(account_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=f"admin_edit_acc:{account_id}")
    builder.button(text="🗑 Удалить",        callback_data=f"admin_del_acc:{account_id}")
    builder.button(text="◀️ Назад",          callback_data="admin_upload_accs")
    builder.adjust(2, 1)
    return builder.as_markup()


def admin_users_list_kb(users: List[Dict[str, Any]], page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    per_page = 8
    start = page * per_page
    end = start + per_page
    for u in users[start:end]:
        name = u.get("username") or u.get("full_name") or str(u["id"])
        builder.button(text=f"👤 {name}", callback_data=f"admin_user:{u['id']}")
    # Навигация
    row = []
    if page > 0:
        builder.button(text="⬅️ Пред.", callback_data=f"admin_users_page:{page - 1}")
    if end < len(users):
        builder.button(text="➡️ След.", callback_data=f"admin_users_page:{page + 1}")
    builder.button(text="◀️ Назад", callback_data="admin_back")
    builder.adjust(2, *([2] * 4), 2 if (page > 0 or end < len(users)) else 1, 1)
    return builder.as_markup()


def admin_user_detail_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📜 Логи",           callback_data=f"admin_user_logs:{user_id}")
    builder.button(text="◀️ К списку",       callback_data="admin_users")
    builder.adjust(1)
    return builder.as_markup()


def admin_confirm_delete_kb(account_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить",    callback_data=f"admin_del_confirm:{account_id}")
    builder.button(text="❌ Отмена",         callback_data=f"admin_acc:{account_id}")
    builder.adjust(2)
    return builder.as_markup()
