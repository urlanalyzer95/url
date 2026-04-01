import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

print("🚀 ОБУЧЕНИЕ RANDOM FOREST на Dataset 1 (208k)")

df = pd.read_csv('data/processed/url_dataset_features.csv')
print(f"📁 Загружено: {len(df)} записей")

feature_cols = [col for col in df.columns if col not in ['url', 'label']]
X = df[feature_cols]
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

model_rf = RandomForestClassifier(n_estimators=200, max_depth=20, random_state=42, n_jobs=-1)
model_rf.fit(X_train, y_train)

y_pred = model_rf.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\n✅ Точность: {accuracy:.2%}")
print("\n📊 Отчет:")
print(classification_report(y_test, y_pred, target_names=['Safe', 'Phishing']))

joblib.dump(model_rf, 'ml/model_rf.pkl')
with open('ml/feature_columns.txt', 'w') as f:
    f.write('\n'.join(feature_cols))

print("✅ Random Forest: ml/model_rf.pkl")