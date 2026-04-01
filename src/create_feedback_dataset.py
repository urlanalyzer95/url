import sqlite3
import pandas as pd
import sys
from pathlib import Path

# Добавляем путь для импорта ml/features.py
sys.path.append(str(Path(__file__).parent.parent))
from ml.features import extract_features

print("🔄 СОЗДАНИЕ DATASET 2 (XGBoost) из ваших меток...")

# Подключаемся к БД с отзывами
conn = sqlite3.connect('data/feedback.db')

# Извлекаем уникальные URL с пользовательскими метками
df = pd.read_sql_query("""
    SELECT DISTINCT url, user_verdict, COUNT(*) as confirmations
    FROM feedbacks 
    WHERE user_verdict IN ('dangerous', 'safe')
    GROUP BY url, user_verdict
    ORDER BY confirmations DESC
""", conn)

conn.close()

print(f"📊 Найдено уникальных URL: {len(df)}")

# Конвертируем вердикты в числовые метки
df['label'] = df['user_verdict'].map({'dangerous': 1, 'safe': 0})
df = df.dropna(subset=['label'])
df = df[['url', 'label']]

print(f"✅ После фильтрации: {len(df)} записей")
print(f"   Опасных (1): {(df['label'] == 1).sum()}")
print(f"   Безопасных (0): {(df['label'] == 0).sum()}")

# Извлекаем признаки для каждого URL
print("\n⚙️ Извлечение признаков...")
features_list = []
failed_urls = []

for idx, row in df.iterrows():
    try:
        features = extract_features(row['url'])
        features_list.append(features)
    except Exception as e:
        print(f"⚠️ Ошибка при обработке {row['url']}: {e}")
        failed_urls.append(row['url'])

# Создаем DataFrame с признаками
feature_names = [
    'url_length', 'num_dots', 'num_hyphens', 'num_slashes', 'num_params',
    'has_ip', 'has_https', 'has_login', 'has_verify', 'has_account',
    'has_cp.php', 'has_admin', 'is_shortened', 'domain_length'
]

df_features = pd.DataFrame(features_list, columns=feature_names)
df_features['url'] = df['url'].values[:len(features_list)]
df_features['label'] = df['label'].values[:len(features_list)]

# Сохраняем Dataset 2
output_path = 'data/processed/feedback_xgboost.csv'
df_features.to_csv(output_path, index=False)

print(f"\n✅ DATASET 2 СОЗДАН: {output_path}")
print(f"   Размер: {len(df_features)} записей")
print(f"   Признаков: {len(feature_names)}")
print(f"   Пропущено URL: {len(failed_urls)}")

if failed_urls:
    print(f"\n⚠️ Проблемные URL:")
    for url in failed_urls[:5]:
        print(f"   - {url}")

print("\n📊 Статистика по меткам:")
print(df_features['label'].value_counts())