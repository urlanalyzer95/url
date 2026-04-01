"""
Валидация качества данных
"""

import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import Config

def validate_dataset(file_path):
    """Проверка датасета"""
    print(f"🔍 ПРОВЕРКА: {file_path.name}")
    print("=" * 50)
    
    df = pd.read_csv(file_path)
    
    # Общая информация
    print(f"\n📊 ОБЩАЯ ИНФОРМАЦИЯ:")
    print(f"   Записей: {len(df):,}")
    print(f"   Колонок: {len(df.columns)}")
    
    # Пропуски
    print(f"\n🔎 ПРОВЕРКА НА ПРОПУСКИ:")
    missing = df.isnull().sum()
    if missing.sum() == 0:
        print("   ✅ Пропусков нет")
    else:
        print(f"   ⚠️ Найдено пропусков:\n{missing[missing > 0]}")
    
    # Дубликаты
    print(f"\n🔎 ПРОВЕРКА НА ДУБЛИКАТЫ:")
    duplicates = df.duplicated(subset=['url']).sum()
    if duplicates == 0:
        print("   ✅ Дубликатов нет")
    else:
        print(f"   ⚠️ Найдено дубликатов URL: {duplicates}")
    
    # Лейблы
    print(f"\n🔎 ПРОВЕРКА ЛЕЙБЛОВ:")
    if 'label' in df.columns:
        label_counts = df['label'].value_counts()
        print(f"   0 (безопасные): {label_counts.get(0, 0):,}")
        print(f"   1 (опасные): {label_counts.get(1, 0):,}")
        
        if len(label_counts) == 2:
            ratio = min(label_counts) / max(label_counts)
            if ratio < 0.5:
                print(f"   ⚠️ Дисбаланс классов: {ratio:.2f}")
            else:
                print(f"   ✅ Хороший баланс: {ratio:.2f}")
    else:
        print("   ⚠️ Колонка 'label' не найдена")
    
    # Признаки
    print(f"\n🔎 ПРОВЕРКА ПРИЗНАКОВ:")
    feature_cols = [c for c in df.columns if c not in ['url', 'label']]
    for col in feature_cols[:3]:  # Первые 3 признака
        print(f"   {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}")
    
    print("\n✅ ПРОВЕРКА ЗАВЕРШЕНА")
    return df

if __name__ == '__main__':
    Config.init_dirs()
    
    # Проверяем новый датасет
    new_dataset = Config.PROCESSED_DATA_DIR / 'url_dataset_features_v2.csv'
    if new_dataset.exists():
        validate_dataset(new_dataset)
    else:
        print("❌ Новый датасет не найден!")
        
        # Проверяем старый
        old_dataset = Config.PROCESSED_DATA_DIR / 'url_dataset_features.csv'
        if old_dataset.exists():
            print("\n⚠️ Проверяем старый датасет:")
            validate_dataset(old_dataset)
