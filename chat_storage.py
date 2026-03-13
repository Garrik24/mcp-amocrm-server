"""
Модуль хранения чат-сообщений из webhook amoCRM (Авито, WhatsApp, Telegram).
SQLite-хранилище для message[add] событий.
"""

import sqlite3
import os
import json
import time
from datetime import datetime, timezone, timedelta

CHAT_DB_PATH = os.getenv("CHAT_DB_PATH", "/tmp/chat_messages.db")

# Московское время UTC+3
MSK = timezone(timedelta(hours=3))


def get_db() -> sqlite3.Connection:
    """Подключение к SQLite + создание таблицы если нет."""
    conn = sqlite3.connect(CHAT_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            chat_id TEXT,
            lead_id INTEGER,
            contact_id INTEGER,
            author_name TEXT,
            author_id TEXT,
            text TEXT,
            origin TEXT,
            is_incoming INTEGER DEFAULT 1,
            media_url TEXT,
            media_type TEXT,
            created_at INTEGER,
            raw_payload TEXT,
            inserted_at INTEGER DEFAULT (strftime('%s', 'now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_lead_id ON chat_messages(lead_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_contact_id ON chat_messages(contact_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_messages(created_at)")
    conn.commit()
    return conn


def parse_webhook_messages(payload: dict) -> list[dict]:
    """Парсинг webhook от amoCRM — извлечение message[add] событий."""
    messages = []
    msg_add = None

    if isinstance(payload, dict):
        msg_data = payload.get("message", {})
        if isinstance(msg_data, dict):
            msg_add = msg_data.get("add")

    if not msg_add or not isinstance(msg_add, list):
        return messages

    for item in msg_add:
        author = item.get("author", {}) or {}
        attachment = item.get("attachment", {}) or {}

        # element_type: "1" = lead, "2" = contact
        element_id = item.get("element_id")
        element_type = str(item.get("element_type", ""))
        lead_id = int(element_id) if element_id and element_type == "1" else None
        contact_id = int(element_id) if element_id and element_type == "2" else None

        created_at = item.get("created_at")
        if created_at is not None:
            try:
                created_at = int(created_at)
            except (ValueError, TypeError):
                created_at = int(time.time())

        msg = {
            "message_id": item.get("id"),
            "chat_id": item.get("chat_id"),
            "lead_id": lead_id,
            "contact_id": contact_id,
            "author_name": author.get("name", ""),
            "author_id": str(author.get("id", "")),
            "text": item.get("text", ""),
            "origin": item.get("origin", ""),
            "is_incoming": 1 if not author.get("type") == "contact" else 1,
            "media_url": attachment.get("link"),
            "media_type": attachment.get("type"),
            "created_at": created_at,
            "raw_payload": json.dumps(item, ensure_ascii=False, default=str),
        }

        # Определяем направление: если автор — бот/менеджер, то исходящее
        # В amoCRM: type=contact — клиент (входящее), иначе — исходящее
        author_type = author.get("type", "")
        if author_type in ("user", "bot", "system"):
            msg["is_incoming"] = 0
        else:
            msg["is_incoming"] = 1

        messages.append(msg)

    return messages


def save_message(msg: dict) -> bool:
    """Сохранить сообщение в БД. Возвращает True если записано (не дубликат)."""
    try:
        db = get_db()
        db.execute("""
            INSERT OR IGNORE INTO chat_messages
            (message_id, chat_id, lead_id, contact_id, author_name, author_id,
             text, origin, is_incoming, media_url, media_type, created_at, raw_payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg.get("message_id"),
            msg.get("chat_id"),
            msg.get("lead_id"),
            msg.get("contact_id"),
            msg.get("author_name"),
            msg.get("author_id"),
            msg.get("text"),
            msg.get("origin"),
            msg.get("is_incoming", 1),
            msg.get("media_url"),
            msg.get("media_type"),
            msg.get("created_at"),
            msg.get("raw_payload"),
        ))
        db.commit()
        return db.total_changes > 0
    except Exception:
        return False
    finally:
        db.close()


def _rows_to_dicts(rows) -> list[dict]:
    """Конвертация sqlite3.Row в список словарей."""
    return [dict(row) for row in rows]


def get_messages_by_lead(lead_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    """Получить сообщения по ID сделки."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM chat_messages WHERE lead_id = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (lead_id, limit, offset)
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        db.close()


def get_messages_by_contact(contact_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    """Получить сообщения по ID контакта."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM chat_messages WHERE contact_id = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (contact_id, limit, offset)
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        db.close()


def get_messages_by_chat(chat_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Получить сообщения по ID чата."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM chat_messages WHERE chat_id = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (chat_id, limit, offset)
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        db.close()


def get_recent_messages(limit: int = 20) -> list[dict]:
    """Получить последние сообщения из всех каналов."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        db.close()


def search_messages(query: str, limit: int = 20) -> list[dict]:
    """Поиск по тексту сообщений (LIKE)."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM chat_messages WHERE text LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        db.close()


def get_stats() -> dict:
    """Статистика: всего сообщений, за сегодня, по каналам."""
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]

        today_start = int(datetime.now(MSK).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        today = db.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE created_at >= ?", (today_start,)
        ).fetchone()[0]

        by_origin_rows = db.execute(
            "SELECT origin, COUNT(*) as cnt FROM chat_messages GROUP BY origin ORDER BY cnt DESC"
        ).fetchall()
        by_origin = {row["origin"]: row["cnt"] for row in by_origin_rows}

        return {
            "total": total,
            "today": today,
            "by_origin": by_origin
        }
    finally:
        db.close()


def format_chat_history(messages: list[dict]) -> str:
    """Форматирование истории чата для Claude."""
    if not messages:
        return "Сообщений не найдено."

    # Группируем по origin
    origins = {}
    for msg in messages:
        origin = msg.get("origin", "unknown")
        origins.setdefault(origin, []).append(msg)

    lines = []
    for origin, msgs in origins.items():
        lines.append(f"Канал: {origin} | Сообщений: {len(msgs)}")
        lines.append("-" * 40)
        for msg in sorted(msgs, key=lambda m: m.get("created_at") or 0):
            ts = msg.get("created_at")
            if ts:
                dt = datetime.fromtimestamp(ts, tz=MSK)
                time_str = dt.strftime("%d.%m %H:%M")
            else:
                time_str = "??:??"

            direction = "←" if msg.get("is_incoming") else "→"
            author = msg.get("author_name", "")
            text = msg.get("text", "")

            media = ""
            if msg.get("media_url"):
                media = f" [{msg.get('media_type', 'файл')}]"

            lines.append(f"[{time_str}] {direction} {author}: {text}{media}")
        lines.append("")

    return "\n".join(lines)
