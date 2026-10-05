import sqlite3
from pathlib import Path


# ---------------------------------------------------------
# Database location
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "learn_ai.db"


# ---------------------------------------------------------
# Connection
# ---------------------------------------------------------

def get_connection():
    """Return a SQLite connection to the Learn AI database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------

def init_db():
    """Create all required tables if they do not already exist."""

    connection = get_connection()
    cursor = connection.cursor()

    # Chats
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            module TEXT,
            option TEXT
        )
        """
    )

    # Messages
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            module TEXT,
            option TEXT,
            attachments TEXT,
            created_at TEXT NOT NULL,

            FOREIGN KEY (chat_id)
                REFERENCES chats(id)
                ON DELETE CASCADE
        )
        """
    )

    # Uploaded PDF metadata
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            name TEXT NOT NULL,
            size INTEGER,
            file_type TEXT,
            file_path TEXT,
            created_at TEXT NOT NULL,

            FOREIGN KEY (chat_id)
                REFERENCES chats(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.commit()
    connection.close()


# ---------------------------------------------------------
# Chat operations
# ---------------------------------------------------------

def save_chat(chat_id, title, created_at, module=None, option=None):
    """Create or update a chat."""

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO chats (
            id,
            title,
            created_at,
            module,
            option
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            module = excluded.module,
            option = excluded.option
        """,
        (
            chat_id,
            title,
            created_at,
            module,
            option,
        ),
    )

    connection.commit()
    connection.close()


def load_chats():
    """Load all saved chats."""

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            title,
            created_at,
            module,
            option
        FROM chats
        ORDER BY created_at DESC
        """
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


def delete_chat(chat_id):
    """Delete a chat and its related messages/documents."""

    connection = get_connection()

    connection.execute(
        "DELETE FROM messages WHERE chat_id = ?",
        (chat_id,),
    )

    connection.execute(
        "DELETE FROM documents WHERE chat_id = ?",
        (chat_id,),
    )

    connection.execute(
        "DELETE FROM chats WHERE id = ?",
        (chat_id,),
    )

    connection.commit()
    connection.close()


# ---------------------------------------------------------
# Message operations
# ---------------------------------------------------------

def save_message(
    chat_id,
    role,
    content,
    module=None,
    option=None,
    attachments=None,
    created_at=None,
):
    """Save one user or assistant message."""

    if created_at is None:
        from datetime import datetime

        created_at = datetime.now().isoformat(timespec="seconds")

    import json

    attachments_json = json.dumps(attachments or [])

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO messages (
            chat_id,
            role,
            content,
            module,
            option,
            attachments,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            role,
            content,
            module,
            option,
            attachments_json,
            created_at,
        ),
    )

    message_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return message_id


def load_messages(chat_id):
    """Load all messages belonging to a chat."""

    import json

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            chat_id,
            role,
            content,
            module,
            option,
            attachments,
            created_at
        FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (chat_id,),
    ).fetchall()

    connection.close()

    messages = []

    for row in rows:
        message = dict(row)

        try:
            message["attachments"] = json.loads(
                message.get("attachments") or "[]"
            )
        except json.JSONDecodeError:
            message["attachments"] = []

        messages.append(message)

    return messages


# ---------------------------------------------------------
# Document operations
# ---------------------------------------------------------

def save_document(
    chat_id,
    name,
    size,
    file_type,
    file_path,
    created_at=None,
):
    """Save uploaded PDF metadata."""

    if created_at is None:
        from datetime import datetime

        created_at = datetime.now().isoformat(timespec="seconds")

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO documents (
            chat_id,
            name,
            size,
            file_type,
            file_path,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            name,
            size,
            file_type,
            file_path,
            created_at,
        ),
    )

    document_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return document_id


def load_documents(chat_id):
    """Load uploaded document metadata for a chat."""

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            id,
            chat_id,
            name,
            size,
            file_type,
            file_path,
            created_at
        FROM documents
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (chat_id,),
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]