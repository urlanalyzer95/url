import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import xgboost as xgb
from config import Config
from logger import logger

def train_models():
    """Обучение Random Forest и XGBoost моделей"""
    
    logger.info("🚀 Начало обучения моделей")
    
    # Загрузка данных
    dataset_path = Config.DATA_DIR / 'processed' / 'url_dataset_features.csv'
    if not dataset_path.exists():
        logger.error(f"❌ Датасет не найден: {dataset_path}")
        return False
    
    df = pd.read_csv(dataset_path)
    logger.info(f"📊 Загружено {len(df)} записей")
    
    # Подготовка данных
    X = df[Config.FEATURE_COLS]
    y = df['label']
    
    # Разделение на train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"📊 Train: {len(X_train)}, Test: {len(X_test)}")
    logger.info(f"📊 Распределение классов - 0: {(y==0).sum()}, 1: {(y==1).sum()}")
    
    # 1. Обучение Random Forest
    logger.info("\n🌲 Обучение Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    
    # Оценка Random Forest
    rf_pred = rf_model.predict(X_test)
    rf_proba = rf_model.predict_proba(X_test)[:, 1]
    
    logger.info("\n📊 Random Forest результаты:")
    logger.info(f"   AUC-ROC: {roc_auc_score(y_test, rf_proba):.4f}")
    logger.info(f"\n{classification_report(y_test, rf_pred)}")
    
    # 2. Обучение XGBoost
    logger.info("\n⚡ Обучение XGBoost...")
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
    
    # Оценка XGBoost
    xgb_pred = xgb_model.predict(X_test)
    xgb_proba = xgb_model.predict_proba(X_test)[:, 1]
    
    logger.info("\n📊 XGBoost результаты:")
    logger.info(f"   AUC-ROC: {roc_auc_score(y_test, xgb_proba):.4f}")
    logger.info(f"\n{classification_report(y_test, xgb_pred)}")
    
    # 3. Ансамбль (усреднение)
    ensemble_proba = (rf_proba + xgb_proba) / 2
    ensemble_pred = (ensemble_proba > 0.5).astype(int)
    
    logger.info("\n🎯 Ансамбль результаты:")
    logger.info(f"   AUC-ROC: {roc_auc_score(y_test, ensemble_proba):.4f}")
    logger.info(f"\n{classification_report(y_test, ensemble_pred)}")
    
    # Сохранение моделей
    Config.MODELS_DIR.mkdir(exist_ok=True)
    
    joblib.dump(rf_model, Config.RANDOM_FOREST_PATH)
    logger.info(f"✅ Random Forest сохранен: {Config.RANDOM_FOREST_PATH}")
    
    joblib.dump(xgb_model, Config.XGBOOST_PATH)
    logger.info(f"✅ XGBoost сохранен: {Config.XGBOOST_PATH}")
    
    # Сохраняем метрики
    metrics = {
        'random_forest': {
            'auc_roc': float(roc_auc_score(y_test, rf_proba)),
            'accuracy': float((rf_pred == y_test).mean())
        },
        'xgboost': {
            'auc_roc': float(roc_auc_score(y_test, xgb_proba)),
            'accuracy': float((xgb_pred == y_test).mean())
        },
        'ensemble': {
            'auc_roc': float(roc_auc_score(y_test, ensemble_proba)),
            'accuracy': float((ensemble_pred == y_test).mean())
        }
    }
    
    import json
    with open(Config.MODELS_DIR / 'metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    logger.info("\n✅ Обучение завершено!")
    return True

if __name__ == '__main__':
    Config.init_dirs()
    train_models()
