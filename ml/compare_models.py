import pandas as pd
import joblib
from sklearn.metrics import accuracy_score, roc_auc_score
from pathlib import Path

print("📊 СРАВНЕНИЕ МОДЕЛЕЙ")
print("=" * 50)

# Загружаем датасет
dataset_path = Path("data/processed/url_dataset_features.csv")
df = pd.read_csv(dataset_path)
feature_cols = [c for c in df.columns if c not in ["url", "label"]]
X = df[feature_cols]
y = df["label"]
print(f"📊 Тестовых примеров: {len(X)}")

# Загружаем модели
models_dir = Path("ml/models")

if (models_dir / "random_forest.pkl").exists():
    rf = joblib.load(models_dir / "random_forest.pkl")
    rf_pred = rf.predict(X)
    rf_proba = rf.predict_proba(X)[:, 1]
    print(f"\n🌲 RANDOM FOREST:")
    print(f"   Accuracy: {accuracy_score(y, rf_pred):.4f}")
    print(f"   AUC-ROC: {roc_auc_score(y, rf_proba):.4f}")
else:
    print("❌ Random Forest модель не найдена")

if (models_dir / "xgboost.pkl").exists():
    xgb = joblib.load(models_dir / "xgboost.pkl")
    xgb_pred = xgb.predict(X)
    xgb_proba = xgb.predict_proba(X)[:, 1]
    print(f"\n⚡ XGBOOST:")
    print(f"   Accuracy: {accuracy_score(y, xgb_pred):.4f}")
    print(f"   AUC-ROC: {roc_auc_score(y, xgb_proba):.4f}")
else:
    print("❌ XGBoost модель не найдена")