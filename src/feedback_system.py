import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import os

class FeedbackSystem:
    def __init__(self, db_path='data/feedback.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """Инициализация БД"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                model_verdict TEXT,
                user_verdict TEXT,
                user_comment TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_feedback(self, url, model_verdict, user_verdict, user_comment=''):
        """Добавить отзыв"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT INTO feedbacks (url, model_verdict, user_verdict, user_comment)
                VALUES (?, ?, ?, ?)
            ''', (url, model_verdict, user_verdict, user_comment))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_all_feedback(self, limit=100):
        """Получить все отзывы"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(f'''
            SELECT * FROM feedbacks ORDER BY timestamp DESC LIMIT {limit}
        ''', conn)
        conn.close()
        return df
    
    def get_stats(self):
        """Статистика"""
        conn = sqlite3.connect(self.db_path)
        total = conn.execute('SELECT COUNT(*) FROM feedbacks').fetchone()[0]
        mismatches = conn.execute('''
            SELECT COUNT(*) FROM feedbacks 
            WHERE model_verdict != user_verdict AND model_verdict IS NOT NULL
        ''').fetchone()[0]
        conn.close()
        
        accuracy = 100 if total == 0 else max(0, 100 * (1 - mismatches / total))
        return {
            'total_feedback': total,
            'mismatches': mismatches,
            'accuracy_estimate': round(accuracy, 1)
        }
