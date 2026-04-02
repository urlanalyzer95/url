import sqlite3
import os
from datetime import datetime

class FeedbackManager:
    def __init__(self, db_path="data/feedback.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    prediction INTEGER NOT NULL,
                    actual INTEGER NOT NULL,
                    comment TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def add(self, url, prediction, actual, comment=""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO feedback (url, prediction, actual, comment) VALUES (?, ?, ?, ?)',
                (url, int(prediction), int(actual), comment)
            )
    
    def get_all(self, limit=100):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT * FROM feedback ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            )
            return [{
                'id': row[0], 'url': row[1], 'prediction': bool(row[2]),
                'actual': bool(row[3]), 'comment': row[4], 'timestamp': row[5]
            } for row in cursor.fetchall()]
    
    def count(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM feedback')
            return cursor.fetchone()[0]
