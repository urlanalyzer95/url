"""
Подготовка нового датасета для дообучения
"""

import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import Config

def prepare_dataset():
    """Подготовка нового датасета с учетом отзывов"""
    print("🔄 ПОДГОТОВКА НОВОГО ДАТАСЕТА...")
    
    # 1. Загружаем основной датасет
    main_path = Config.PROCESSED_DATA_DIR / 'url_dataset_features.csv'
    if not main_path.exists():
        print(f"❌ Основной датасет не найден: {main_path}")
        return None
    
    main_df = pd.read_csv(main_path)
    print(f"📁 Основной датасет: {len(main_df)} записей")
    
    # 2. Загружаем новые примеры из отзывов
    new_examples_path = Config.DATA_DIR / 'new_training_examples.csv'
    if not new_examples_path.exists():
        print("⚠️ Нет новых примеров из отзывов")
        main_df.to_csv(Config.PROCESSED_DATA_DIR / 'url_dataset_features_v2.csv', index=False)
        return main_df
    
    feedback_df = pd.read_csv(new_examples_path)
    print(f"📁 Новые примеры: {len(feedback_df)} записей")
    
    # 3. Извлекаем признаки для новых URL
    print("\n⚙️ Извлечение признаков...")
    
    # Импортируем функцию из features.py (из ml папки)
    sys.path.append(str(Config.BASE_DIR / 'ml'))
    from features import extract_features
    
    new_features = []
    valid_urls = []
    valid_labels = []
    
    for idx, row in feedback_df.iterrows():
        try:
            url = row['url']
            label = row['label']
            
            features = extract_features(url)
            new_features.append(features)
            valid_urls.append(url)
            valid_labels.append(label)
            
        except Exception as e:
            print(f"⚠️ Ошибка для {row['url'][:50]}: {e}")
            continue
    
    if not new_features:
        print("❌ Не удалось извлечь признаки")
        return main_df
    
    # Создаем DataFrame с признаками
    feature_cols = [c for c in main_df.columns if c not in ['url', 'label']]
    new_df = pd.DataFrame(new_features, columns=feature_cols)
    new_df['url'] = valid_urls
    new_df['label'] = valid_labels
    
    # 4. Объединяем датасеты
    combined_df = pd.concat([main_df, new_df], ignore_index=True)
    
    # 5. Удаляем дубликаты
    before = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=['url'], keep='last')
    after = len(combined_df)
    print(f"\n🗑️ Удалено дубликатов: {before - after}")
    
    # 6. Статистика
    print(f"\n📊 РАСПРЕДЕЛЕНИЕ КЛАССОВ:")
    print(f"   Безопасных (0): {(combined_df['label'] == 0).sum()}")
    print(f"   Опасных (1): {(combined_df['label'] == 1).sum()}")
    print(f"   Всего: {len(combined_df)}")
    
    # 7. Сохраняем
    output_path = Config.PROCESSED_DATA_DIR / 'url_dataset_features_v2.csv'
    combined_df.to_csv(output_path, index=False)
    print(f"\n✅ НОВЫЙ ДАТАСЕТ СОХРАНЁН:")
    print(f"   {output_path}")
    print(f"   Размер: {len(combined_df)} записей")
    
    return combined_df

if __name__ == '__main__':
    Config.init_dirs()
    prepare_dataset()
