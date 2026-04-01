"""
Экспорт отзывов из feedback.db
"""

import sys
import pandas as pd
import sqlite3
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

def export_feedback():
    """Экспорт всех отзывов"""
    print("📤 ЭКСПОРТ ОТЗЫВОВ...")
    
    db_path = Path('data/feedback.db')
    if not db_path.exists():
        print(f"⚠️ База данных не найдена: {db_path}")
        return None
    
    conn = sqlite3.connect(db_path)
    
    # Все отзывы
    all_feedback = pd.read_sql_query("""
        SELECT id, url, model_verdict, user_verdict, 
               user_comment, timestamp, is_processed
        FROM feedbacks 
        ORDER BY timestamp DESC
    """, conn)
    
    # Только новые (необработанные) для дообучения
    new_feedback = pd.read_sql_query("""
        SELECT url, user_verdict
        FROM feedbacks 
        WHERE is_processed = 0 
        AND user_verdict IN ('safe', 'dangerous')
        ORDER BY timestamp DESC
    """, conn)
    
    conn.close()
    
    # Сохраняем
    if not all_feedback.empty:
        all_feedback.to_csv('data/feedback_all.csv', index=False)
        all_feedback.to_json('data/feedback_all.json', 
                            orient='records', indent=2, force_ascii=False)
        print(f"✅ Экспортировано {len(all_feedback)} отзывов")
    
    if not new_feedback.empty:
        # Конвертируем в формат для ML
        new_feedback['label'] = new_feedback['user_verdict'].map({
            'safe': 0,
            'dangerous': 1
        })
        new_feedback = new_feedback.dropna()
        new_feedback[['url', 'label']].to_csv(
            'data/new_training_examples.csv', index=False
        )
        print(f"✅ Найдено {len(new_feedback)} новых примеров для дообучения")
        
        # Статистика
        print(f"\n📊 Новые примеры:")
        print(f"   Безопасных (0): {(new_feedback['label'] == 0).sum()}")
        print(f"   Опасных (1): {(new_feedback['label'] == 1).sum()}")
    
    return new_feedback

if __name__ == '__main__':
    export_feedback()
