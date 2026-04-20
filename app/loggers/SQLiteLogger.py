import sqlite3
import os
from datetime import datetime
from .BaseLogger import BaseLogger
import json
from pathlib import Path

class SQLiteLogger(BaseLogger):

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv("LOG_DB_PATH", "")
            if db_path:
                db_path = Path(db_path)
            else:
                db_path = Path(__file__).parent.parent.parent / "logs" / "logs.db"

        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # FastAPI puede ejecutar handlers en distintos hilos.
        # Esta opcion evita el error de "SQLite objects created in a thread...".
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        journal_mode = os.getenv("SQLITE_JOURNAL_MODE", "").strip().upper()
        if journal_mode:
            self.conn.execute(f"PRAGMA journal_mode={journal_mode}")
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                question TEXT,
                answer TEXT,
                context_length INTEGER,
                num_sources INTEGER,
                response_time REAL,
                sources TEXT,
                mode TEXT,
                selected_sources TEXT
            )
        ''')
        self._ensure_column(cursor, "logs", "mode", "TEXT")
        self._ensure_column(cursor, "logs", "selected_sources", "TEXT")
        self.conn.commit()

    def _ensure_column(self, cursor, table_name: str, column_name: str, column_type: str):
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        if column_name not in columns:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )

    def log_query(self, log_data: dict):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO logs (timestamp, question, answer, context_length, num_sources, response_time, sources, mode, selected_sources)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            log_data.get("question", ""),
            log_data.get("answer", ""),
            log_data.get("context_length", 0),
            log_data.get("num_sources", 0),
            log_data.get("response_time", 0.0),
            json.dumps(log_data.get("sources", [])),
            log_data.get("mode", "manual"),
            json.dumps(log_data.get("selected_sources", []))
        ))
        self.conn.commit()