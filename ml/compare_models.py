"""
Сравнение Random Forest и XGBoost
"""

import pandas as pd
import joblib
import numpy as np
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
from pathlib import Path

def compare_models():
    """Сравнение двух моделей"""
    print("📊 СРАВНЕНИЕ МОДЕЛЕЙ")
    print("=" * 50)
    
    # 1. Загружаем датасет
    dataset_path = Path('data/processed/url_dataset_features_v2.csv')
    if not dataset_path.exists():
        print(f"❌ Датасет не найден: {dataset_path}")
        return
    
    df = pd.read_csv(dataset_path)
    feature_cols = [c for c in df.columns if c not in ['url', 'label']]
    X = df[feature_cols]
    y = df['label']
    
    print(f"📊 Тестовых примеров: {len(X)}")
    
    # 2. Загружаем модели
    models_dir = Path('ml/models')
    
    rf_path = models_dir / 'random_forest.pkl'
    xgb_path = models_dir / 'xgboost.pkl'
    
    if not rf_path.exists():
        print(f"❌ Модель Random Forest не найдена: {rf_path}")
        return
    
    if not xgb_path.exists():
        print(f"❌ Модель XGBoost не найдена: {xgb_path}")
        return
    
    rf_model = joblib.load(rf_path)
    xgb_model = joblib.load(xgb_path)
    
    print("✅ Модели загружены\n")
    
    # 3. Предсказания
    print("🔮 Предсказания:")
    
    rf_proba = rf_model.predict_proba(X)[:, 1]
    xgb_proba = xgb_model.predict_proba(X)[:, 1]
    
    rf_pred = (rf_proba > 0.5).astype(int)
    xgb_pred = (xgb_proba > 0.5).astype(int)
    
    # Ансамбль (усреднение)
    ensemble_proba = (rf_proba + xgb_proba) / 2
    ensemble_pred = (ensemble_proba > 0.5).astype(int)
    
    # 4. Результаты
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ:")
    print("=" * 50)
    
    print("\n🌲 RANDOM FOREST:")
    print(f"   Accuracy: {accuracy_score(y, rf_pred):.4f}")
    print(f"   AUC-ROC: {roc_auc_score(y, rf_proba):.4f}")
    
    print("\n⚡ XGBOOST:")
    print(f"   Accuracy: {accuracy_score(y, xgb_pred):.4f}")
    print(f"   AUC-ROC: {roc_auc_score(y, xgb_proba):.4f}")
    
    print("\n🎯 АНСАМБЛЬ (усреднение):")
    print(f"   Accuracy: {accuracy_score(y, ensemble_pred):.4f}")
    print(f"   AUC-ROC: {roc_auc_score(y, ensemble_proba):.4f}")
    
    # 5. Детальный отчет
    print("\n" + "=" * 50)
    print("📋 ДЕТАЛЬНЫЙ ОТЧЕТ:")
    print("=" * 50)
    
    print("\n🌲 RANDOM FOREST:")
    print(classification_report(y, rf_pred))
    
    print("\n⚡ XGBOOST:")
    print(classification_report(y, xgb_pred))
    
    print("\n🎯 АНСАМБЛЬ:")
    print(classification_report(y, ensemble_pred))
    
    # 6. Сохраняем результаты
    results = {
        'random_forest': {
            'accuracy': float(accuracy_score(y, rf_pred)),
            'auc_roc': float(roc_auc_score(y, rf_proba))
        },
        'xgboost': {
            'accuracy': float(accuracy_score(y, xgb_pred)),
            'auc_roc': float(roc_auc_score(y, xgb_proba))
        },
        'ensemble': {
            'accuracy': float(accuracy_score(y, ensemble_pred)),
            'auc_roc': float(roc_auc_score(y, ensemble_proba))
        }
    }
    
    import json
    with open(models_dir / 'comparison.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Результаты сохранены: {models_dir / 'comparison.json'}")
    
    return results

if __name__ == '__main__':
    compare_models()
