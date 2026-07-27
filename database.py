"""База данных — SQLite через aiosqlite."""
import aiosqlite
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import config

logger = logging.getLogger(__name__)

DB_PATH = config.db_path


async def init_db() -> None:
    """Создаёт таблицы при первом запуске."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY,
            username    TEXT,
            full_name   TEXT,
            balance     REAL    NOT NULL DEFAULT 0,
            agreed_tos  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            last_seen   TEXT    NOT NULL DEFAULT (datetime('now')),
            is_banned   INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,
            description  TEXT,
            price        REAL    NOT NULL,
            email        TEXT    NOT NULL,
            email_pass   TEXT    NOT NULL,
            acc_number   TEXT    NOT NULL,
            acc_pass     TEXT    NOT NULL,
            note         TEXT    NOT NULL DEFAULT '',
            is_sold      INTEGER NOT NULL DEFAULT 0,
            sold_to      INTEGER,
            sold_at      TEXT,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            account_id  INTEGER NOT NULL,
            amount      REAL    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id)    REFERENCES users(id),
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            rollypay_id     TEXT,
            order_id        TEXT    UNIQUE NOT NULL,
            amount          REAL    NOT NULL,
            status          TEXT    NOT NULL DEFAULT 'created',
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            action      TEXT    NOT NULL,
            details     TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        """)
        await db.commit()
    logger.info("DB initialized at %s", DB_PATH)


# ──────────────────────────────────────────────────────────────
#  Users
# ──────────────────────────────────────────────────────────────

async def get_or_create_user(user_id: int, username: Optional[str], full_name: str) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username=?, full_name=?, last_seen=datetime('now') WHERE id=?",
                (username, full_name, user_id)
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
        else:
            await db.execute(
                "INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)",
                (user_id, username, full_name)
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
        return dict(row)


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_agreed_tos(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET agreed_tos=1 WHERE id=?", (user_id,))
        await db.commit()


async def update_balance(user_id: int, delta: float) -> float:
    """Изменяет баланс на delta (может быть отрицательным). Возвращает новый баланс."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE users SET balance = ROUND(balance + ?, 2) WHERE id = ?",
            (delta, user_id)
        )
        await db.commit()
        cursor = await db.execute("SELECT balance FROM users WHERE id=?", (user_id,))
        row = await cursor.fetchone()
        return row["balance"] if row else 0.0


async def get_all_users() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────
#  Accounts
# ──────────────────────────────────────────────────────────────

async def add_account(item: Dict[str, Any]) -> int:
    """Добавляет один аккаунт, возвращает его id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO accounts
               (title, description, price, email, email_pass, acc_number, acc_pass, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item["title"],
                item.get("description", ""),
                item["price"],
                item["email"],
                item["email_pass"],
                item["acc_number"],
                item["acc_pass"],
                item.get("note", ""),
            )
        )
        await db.commit()
        return cursor.lastrowid


async def get_account(account_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM accounts WHERE id=?", (account_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_available_accounts() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM accounts WHERE is_sold=0 ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_all_accounts() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM accounts ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_account(
    account_id: int,
    title: str,
    description: str,
    price: float,
    email: str,
    email_pass: str,
    acc_number: str,
    acc_pass: str,
    note: str,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE accounts
               SET title=?, description=?, price=?,
                   email=?, email_pass=?, acc_number=?, acc_pass=?, note=?
               WHERE id=?""",
            (title, description, price, email, email_pass, acc_number, acc_pass, note, account_id)
        )
        await db.commit()


async def delete_account(account_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM accounts WHERE id=?", (account_id,))
        await db.commit()


async def sell_account(account_id: int, user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE accounts SET is_sold=1, sold_to=?, sold_at=datetime('now') WHERE id=?",
            (user_id, account_id)
        )
        await db.commit()


# ──────────────────────────────────────────────────────────────
#  Orders
# ──────────────────────────────────────────────────────────────

async def create_order(user_id: int, account_id: int, amount: float) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO orders (user_id, account_id, amount) VALUES (?, ?, ?)",
            (user_id, account_id, amount)
        )
        await db.commit()
        return cursor.lastrowid


async def get_last_order(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT o.*, a.title FROM orders o
               JOIN accounts a ON a.id = o.account_id
               WHERE o.user_id=? ORDER BY o.created_at DESC LIMIT 1""",
            (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ──────────────────────────────────────────────────────────────
#  Payments
# ──────────────────────────────────────────────────────────────

async def create_payment_record(user_id: int, order_id: str, amount: float) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO payments (user_id, order_id, amount) VALUES (?, ?, ?)",
            (user_id, order_id, amount)
        )
        await db.commit()
        return cursor.lastrowid


async def update_payment_status(order_id: str, status: str, rollypay_id: Optional[str] = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        if rollypay_id:
            await db.execute(
                "UPDATE payments SET status=?, rollypay_id=?, updated_at=datetime('now') WHERE order_id=?",
                (status, rollypay_id, order_id)
            )
        else:
            await db.execute(
                "UPDATE payments SET status=?, updated_at=datetime('now') WHERE order_id=?",
                (status, order_id)
            )
        await db.commit()


async def get_payment_by_order(order_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM payments WHERE order_id=?", (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# ──────────────────────────────────────────────────────────────
#  Logs
# ──────────────────────────────────────────────────────────────

async def add_log(user_id: Optional[int], action: str, details: str = "") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
            (user_id, action, details)
        )
        await db.commit()


async def get_user_logs(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM logs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
