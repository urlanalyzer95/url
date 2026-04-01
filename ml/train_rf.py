"""
Обучение Random Forest модели на новом датасете
"""

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from pathlib import Path

def train_random_forest():
    """Обучение Random Forest на новом датасете"""
    print("🌲 ОБУЧЕНИЕ RANDOM FOREST")
    print("=" * 50)
    
    # 1. Загружаем новый датасет от Data-инженера
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
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    
    # 5. Оценка качества
    print("\n📊 ОЦЕНКА КАЧЕСТВА:")
    y_pred = rf_model.predict(X_test)
    y_proba = rf_model.predict_proba(X_test)[:, 1]
    
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    print(f"\nAUC-ROC: {roc_auc_score(y_test, y_proba):.4f}")
    
    print(f"\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # 6. Сохраняем модель
    models_dir = Path('ml/models')
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / 'random_forest.pkl'
    joblib.dump(rf_model, model_path)
    print(f"\n✅ Модель сохранена: {model_path}")
    
    # 7. Сохраняем метрики
    metrics = {
        'accuracy': float((y_pred == y_test).mean()),
        'auc_roc': float(roc_auc_score(y_test, y_proba)),
        'train_size': len(X_train),
        'test_size': len(X_test)
    }
    
    import json
    with open(models_dir / 'rf_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"✅ Метрики сохранены: {models_dir / 'rf_metrics.json'}")
    
    return rf_model

if __name__ == '__main__':
    train_random_forest()
