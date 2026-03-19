import sqlite3
from datetime import datetime
from .BaseLogger import BaseLogger
import json
from pathlib import Path

class SQLiteLogger(BaseLogger):

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'logs' / 'logs.db'

        # FastAPI puede ejecutar handlers en distintos hilos.
        # Esta opcion evita el error de "SQLite objects created in a thread...".
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
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
                sources TEXT
            )
        ''')
        self.conn.commit()

    def log_query(self, log_data: dict):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO logs (timestamp, question, answer, context_length, num_sources, response_time, sources)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            log_data.get("question", ""),
            log_data.get("answer", ""),
            log_data.get("context_length", 0),
            log_data.get("num_sources", 0),
            log_data.get("response_time", 0.0),
            json.dumps(log_data.get("sources", []))
        ))
        self.conn.commit()