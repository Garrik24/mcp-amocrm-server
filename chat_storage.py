"""
Модуль хранения чат-сообщений из webhook amoCRM (Авито, WhatsApp, Telegram).
SQLite-хранилище для message[add] событий.
"""

import sqlite3
import os
import re
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


def _coerce_lists(node):
    """Превращает dict с последовательными числовыми ключами 0..n в list (рекурсивно)."""
    if isinstance(node, dict):
        node = {k: _coerce_lists(v) for k, v in node.items()}
        keys = list(node.keys())
        if keys and all(isinstance(k, str) and k.isdigit() for k in keys):
            idxs = sorted(int(k) for k in keys)
            if idxs == list(range(len(idxs))):
                return [node[str(i)] for i in idxs]
        return node
    if isinstance(node, list):
        return [_coerce_lists(v) for v in node]
    return node


def unflatten(flat: dict) -> dict:
    """PHP-стиль form-ключи amoCRM (a[b][0][c]=v) -> вложенная структура.

    amoCRM шлёт вебхуки как application/x-www-form-urlencoded со скобочными
    ключами вида `message[add][0][text]`. После urldecode это плоский словарь,
    который нужно развернуть во вложенную структуру и нормализовать индексы в списки.
    """
    root: dict = {}
    key_re = re.compile(r"\[([^\]]*)\]")
    for full_key, value in flat.items():
        full_key = str(full_key)
        head = re.match(r"^([^\[]+)", full_key)
        if not head:
            continue
        tokens = [head.group(1)] + key_re.findall(full_key)
        cur = root
        for i, tok in enumerate(tokens):
            if i == len(tokens) - 1:
                cur[tok] = value
            else:
                nxt = cur.get(tok)
                if not isinstance(nxt, dict):
                    nxt = {}
                    cur[tok] = nxt
                cur = nxt
    return _coerce_lists(root)


def parse_webhook_messages(payload: dict) -> list[dict]:
    """Парсинг webhook от amoCRM — извлечение message[add] событий.

    Принимает как плоский словарь скобочных form-ключей (формат amoCRM),
    так и уже вложенную JSON-структуру.
    """
    messages: list[dict] = []

    if not isinstance(payload, dict):
        return messages

    # Если пришли плоские скобочные ключи — разворачиваем
    if any("[" in str(k) for k in payload.keys()):
        payload = unflatten(payload)

    msg_data = payload.get("message")
    msg_add = msg_data.get("add") if isinstance(msg_data, dict) else None
    if isinstance(msg_add, dict):
        # dict здесь — это либо одиночное сообщение без индекса (message[add][id]=...),
        # либо разреженные/непоследовательные индексы (_coerce_lists их не свернул в list).
        if msg_add and all(str(k).isdigit() for k in msg_add.keys()):
            msg_add = [msg_add[k] for k in sorted(msg_add.keys(), key=lambda x: int(x))]
        else:
            msg_add = [msg_add]
    if not isinstance(msg_add, list):
        return messages

    for item in msg_add:
        if not isinstance(item, dict):
            continue
        # Без message_id сообщение не дедуплицируется (UNIQUE допускает много NULL)
        # и засоряет БД через публичный эндпоинт — пропускаем.
        if not item.get("id"):
            continue
        author = item.get("author") or {}
        if not isinstance(author, dict):
            author = {}
        attachment = item.get("attachment") or {}
        if not isinstance(attachment, dict):
            attachment = {}

        # contact_id приходит отдельным полем напрямую
        contact_id = item.get("contact_id")
        try:
            contact_id = int(contact_id) if contact_id else None
        except (ValueError, TypeError):
            contact_id = None

        # lead_id: берём только если вебхук явно указывает сущность-сделку.
        # element_type/element_id ненадёжны (element_type=2 при entity_type=lead),
        # поэтому если поля нет — оставляем None, а app.py дозаполнит через talk_id.
        entity_type = str(item.get("entity_type") or "")
        lead_id = None
        if entity_type == "lead":
            entity_id = item.get("entity_id")
            try:
                lead_id = int(entity_id) if entity_id else None
            except (ValueError, TypeError):
                lead_id = None

        talk_id = item.get("talk_id")

        created_at = item.get("created_at")
        try:
            created_at = int(created_at) if created_at is not None else int(time.time())
        except (ValueError, TypeError):
            created_at = int(time.time())

        # Направление: клиент (внешний автор) — входящее, менеджер/бот — исходящее.
        author_type = str(author.get("type") or "")
        is_incoming = 0 if author_type in ("user", "bot", "system", "internal") else 1

        msg = {
            "message_id": item.get("id"),
            "chat_id": item.get("chat_id"),
            "talk_id": int(talk_id) if str(talk_id or "").isdigit() else None,
            "lead_id": lead_id,
            "contact_id": contact_id,
            "author_name": author.get("name", ""),
            "author_id": str(author.get("id", "")),
            "text": item.get("text", ""),
            "origin": item.get("origin", ""),
            "is_incoming": is_incoming,
            "media_url": attachment.get("link"),
            "media_type": attachment.get("type"),
            "created_at": created_at,
            "raw_payload": json.dumps(item, ensure_ascii=False, default=str),
        }
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
