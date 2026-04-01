import pandas as pd
import numpy as np
import os

print("🔍 Роль 2: Подготовка датасета для спринта 2")

# 1. Отзывы (уже есть)
feedback_path = 'data/feedback_export.csv'
if os.path.exists(feedback_path):
    feedback = pd.read_csv(feedback_path)
    print(f"✅ Отзывы: {len(feedback)} строк")
else:
    print("❌ feedback_export.csv не найден")

# 2. Старый датасет (если есть)
old_path = 'data/processed/url_dataset_features.csv'
if os.path.exists(old_path):
    old_data = pd.read_csv(old_path)
    print(f"✅ Старый датасет: {len(old_data)} строк")
else:
    print("⚠️ url_dataset_features.csv не найден — создаём фейк")
    # Фейковый датасет для демонстрации
    fake_data = pd.DataFrame({
        'url': ['g00gle.com', 'google.com', 'sber-login.ru', 'sberbank.ru', 'bit.ly/test'],
        'label': [1, 0, 1, 0, 1],
        'length': [10, 10, 13, 11, 10]
    })
    fake_data.to_csv(old_path, index=False)
    old_data = fake_data
    print("✅ Фейковый датасет создан")

# 3. Объединение
full_dataset = pd.concat([
    old_data[['url', 'label']].rename(columns={'label': 'true_label'}),
    feedback[['url']].assign(true_label=1)  # Отзывы = фишинг
], ignore_index=True)

# 4. Очистка
full_dataset.drop_duplicates(subset=['url'], inplace=True)
full_dataset = full_dataset[full_dataset['url'].str.len() > 5]

# 5. Сохранение
full_dataset.to_csv('data/full_dataset_sprint2.csv', index=False)
print(f"✅ Полный датасет: {len(full_dataset)} строк → full_dataset_sprint2.csv")

clean_data = full_dataset.copy()
clean_data.to_csv('data/clean_dataset_sprint2.csv', index=False)
print(f"✅ Очищенный датасет: {len(clean_data)} уникальных URL")
print("\n📊 Статистика:")
print(clean_data['true_label'].value_counts() if 'true_label' in clean_data else "Готово!")
print("\n✅ Роль 2 завершена! Передай Роли 1: data/clean_dataset_sprint2.csv")
