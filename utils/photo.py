"""Утилита для отправки сообщений с баннером Selectel Market."""
import os
import logging
from aiogram.types import FSInputFile, Message, CallbackQuery

logger = logging.getLogger(__name__)

_BASE = os.path.dirname(os.path.dirname(__file__))
BANNER_PATH = os.path.join(_BASE, "assets", "banner.jpg")
_CACHE_FILE = os.path.join(_BASE, "assets", ".file_id_cache")

_cached_file_id: str | None = None


# ── Кэш file_id ─────────────────────────────────────────────────────────────

def _load_cache() -> str | None:
    global _cached_file_id
    if _cached_file_id:
        return _cached_file_id
    if os.path.exists(_CACHE_FILE):
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            fid = f.read().strip()
            if fid:
                _cached_file_id = fid
                return fid
    return None


def _save_cache(file_id: str) -> None:
    global _cached_file_id
    _cached_file_id = file_id
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(file_id)
    except Exception as e:
        logger.warning("Не удалось сохранить кэш file_id: %s", e)


def _banner():
    """Возвращает file_id из кэша или FSInputFile при первой отправке."""
    return _load_cache() or FSInputFile(BANNER_PATH)


# ── Публичные функции ────────────────────────────────────────────────────────

async def send_banner(
    message: Message,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> Message:
    """
    Отправляет новое сообщение: баннер + текст в подписи.
    Если текст длиннее 1024 символов — сначала фото, потом текст отдельно.
    """
    if len(text) <= 1024:
        sent = await message.answer_photo(
            photo=_banner(),
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        # Кэшируем file_id
        if sent.photo:
            _save_cache(sent.photo[-1].file_id)
        return sent
    else:
        # Длинный текст: фото без подписи, затем текст
        sent = await message.answer_photo(photo=_banner())
        if sent.photo:
            _save_cache(sent.photo[-1].file_id)
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return sent


async def edit_banner(
    call: CallbackQuery,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> None:
    """
    Редактирует существующее фото-сообщение (меняет подпись).
    Если сообщение не фото (fallback) — редактирует текст.
    """
    try:
        await call.message.edit_caption(
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except Exception:
        # Fallback: сообщение без фото
        try:
            await call.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except Exception as e:
            logger.warning("edit_banner fallback: %s", e)
