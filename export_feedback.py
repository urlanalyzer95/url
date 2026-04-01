import sqlite3
import pandas as pd
import os

print("🔍 Экспорт feedback.db...")

db_path = 'data/feedback.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM feedbacks", conn)
    df.to_csv('data/feedback_export.csv', index=False)
    print(f"✅ Экспорт: {len(df)} отзывов → data/feedback_export.csv")
    conn.close()
else:
    print("⚠️ feedback.db не найдена")
    pd.DataFrame(columns=['id', 'url', 'model_verdict', 'user_verdict', 'timestamp']).to_csv('data/feedback_export.csv', index=False)
    print("✅ Пустой шаблон data/feedback_export.csv создан")
