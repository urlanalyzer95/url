import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from pathlib import Path

print("🌲 ОБУЧЕНИЕ RANDOM FOREST")
print("=" * 50)

# Загружаем датасет
dataset_path = Path("data/processed/url_dataset_features.csv")
if not dataset_path.exists():
    print(f"❌ Датасет не найден: {dataset_path}")
    exit(1)

df = pd.read_csv(dataset_path)
print(f"📊 Загружено: {len(df)} записей")

# Определяем признаки
feature_cols = [c for c in df.columns if c not in ["url", "label"]]
X = df[feature_cols]
y = df["label"]

print(f"📊 Признаков: {len(feature_cols)}")
print(f"📊 Классы: 0={(y==0).sum()}, 1={(y==1).sum()}")

# Разделяем данные
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n📊 Train: {len(X_train)}, Test: {len(X_test)}")

# Обучаем Random Forest
print("\n⚙️ Обучение Random Forest...")
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    random_state=42,
    n_jobs=-1
)
rf_model.fit(X_train, y_train)

# Оценка
y_pred = rf_model.predict(X_test)
y_proba = rf_model.predict_proba(X_test)[:, 1]
print(f"\n📊 AUC-ROC: {roc_auc_score(y_test, y_proba):.4f}")
print(f"📊 Accuracy: {(y_pred == y_test).mean():.4f}")

# Сохраняем модель
models_dir = Path("ml/models")
models_dir.mkdir(exist_ok=True)
joblib.dump(rf_model, models_dir / "random_forest.pkl")
print(f"\n✅ Модель сохранена в ml/models/random_forest.pkl")