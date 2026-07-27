"""Конфигурация бота Selectel Market."""
import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _get_admin_ids() -> List[int]:
    raw = os.getenv("ADMIN_IDS", "")
    ids = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


@dataclass
class Config:
    # Telegram
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: List[int] = field(default_factory=_get_admin_ids)

    # CryptoBot (Crypto Pay)
    cryptobot_token: str = os.getenv("CRYPTOBOT_TOKEN", "")
    cryptobot_testnet: bool = os.getenv("CRYPTOBOT_TESTNET", "false").lower() == "true"

    # Webhook (для приёма колбэков CryptoBot)
    webhook_host: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    webhook_port: int = int(os.getenv("WEBHOOK_PORT", "8080"))
    webhook_path: str = os.getenv("WEBHOOK_PATH", "/webhooks/cryptobot")

    # База данных
    db_path: str = os.getenv("DB_PATH", "market.db")

    # Прочее
    support_username: str = os.getenv("SUPPORT_USERNAME", "support")
    currency: str = "RUB"
    min_topup: int = int(os.getenv("MIN_TOPUP", "50"))
    max_topup: int = int(os.getenv("MAX_TOPUP", "100000"))
    # Комиссия при пополнении (0.03 = 3%). Пользователь платит amount * (1 + commission)
    topup_commission: float = float(os.getenv("TOPUP_COMMISSION", "0.03"))

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


config = Config()
