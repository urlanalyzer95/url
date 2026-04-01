import pandas as pd
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from pathlib import Path

print("⚡ ОБУЧЕНИЕ XGBOOST")
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

# Обучаем XGBoost
print("\n⚙️ Обучение XGBoost...")
xgb_model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    random_state=42,
    use_label_encoder=False,
    eval_metric="logloss"
)
xgb_model.fit(X_train, y_train)

# Оценка
y_pred = xgb_model.predict(X_test)
y_proba = xgb_model.predict_proba(X_test)[:, 1]
print(f"\n📊 AUC-ROC: {roc_auc_score(y_test, y_proba):.4f}")
print(f"📊 Accuracy: {(y_pred == y_test).mean():.4f}")

# Сохраняем модель
models_dir = Path("ml/models")
models_dir.mkdir(exist_ok=True)
joblib.dump(xgb_model, models_dir / "xgboost.pkl")
print(f"\n✅ Модель сохранена в ml/models/xgboost.pkl")