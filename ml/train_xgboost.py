"""
Обучение XGBoost модели на новом датасете
"""

import pandas as pd
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from pathlib import Path

def train_xgboost():
    """Обучение XGBoost на новом датасете"""
    print("⚡ ОБУЧЕНИЕ XGBOOST")
    print("=" * 50)
    
    # 1. Загружаем новый датасет
    dataset_path = Path('data/processed/url_dataset_features_v2.csv')
    if not dataset_path.exists():
        print(f"❌ Датасет не найден: {dataset_path}")
        print("Сначала запусти Data-инженера для подготовки данных!")
        return None
    
    df = pd.read_csv(dataset_path)
    print(f"📊 Загружено записей: {len(df)}")
    
    # 2. Определяем признаки и целевую переменную
    feature_cols = [c for c in df.columns if c not in ['url', 'label']]
    X = df[feature_cols]
    y = df['label']
    
    print(f"📊 Признаков: {len(feature_cols)}")
    print(f"📊 Классы: 0={ (y==0).sum() }, 1={ (y==1).sum() }")
    
    # 3. Разделяем на train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n📊 Train: {len(X_train)}, Test: {len(X_test)}")
    
    # 4. Обучаем модель
    print("\n⚙️ Обучение модели...")
    xgb_model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    xgb_model.fit(X_train, y_train)
    
    # 5. Оценка качества
    print("\n📊 ОЦЕНКА КАЧЕСТВА:")
    y_pred = xgb_model.predict(X_test)
    y_proba = xgb_model.predict_proba(X_test)[:, 1]
    
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    print(f"\nAUC-ROC: {roc_auc_score(y_test, y_proba):.4f}")
    
    print(f"\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # 6. Сохраняем модель
    models_dir = Path('ml/models')
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / 'xgboost.pkl'
    joblib.dump(xgb_model, model_path)
    print(f"\n✅ Модель сохранена: {model_path}")
    
    # 7. Сохраняем метрики
    metrics = {
        'accuracy': float((y_pred == y_test).mean()),
        'auc_roc': float(roc_auc_score(y_test, y_proba)),
        'train_size': len(X_train),
        'test_size': len(X_test)
    }
    
    import json
    with open(models_dir / 'xgb_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"✅ Метрики сохранены: {models_dir / 'xgb_metrics.json'}")
    
    return xgb_model

if __name__ == '__main__':
    train_xgboost()
