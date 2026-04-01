import joblib
import numpy as np
import pandas as pd
from typing import Dict, Tuple
from config import Config
from logger import logger
from src.features import extract_features

class EnsemblePredictor:
    """Ансамбль моделей Random Forest и XGBoost"""
    
    def __init__(self):
        self.random_forest = None
        self.xgboost = None
        self.weights = Config.MODEL_WEIGHTS
        self.load_models()
    
    def load_models(self):
        """Загрузка обеих моделей"""
        try:
            if Config.RANDOM_FOREST_PATH.exists():
                self.random_forest = joblib.load(Config.RANDOM_FOREST_PATH)
                logger.info("✅ Random Forest модель загружена")
            else:
                logger.warning(f"⚠️ Random Forest не найден: {Config.RANDOM_FOREST_PATH}")
        except Exception as e:
            logger.error(f"Ошибка загрузки Random Forest: {e}")
        
        try:
            if Config.XGBOOST_PATH.exists():
                self.xgboost = joblib.load(Config.XGBOOST_PATH)
                logger.info("✅ XGBoost модель загружена")
            else:
                logger.warning(f"⚠️ XGBoost не найден: {Config.XGBOOST_PATH}")
        except Exception as e:
            logger.error(f"Ошибка загрузки XGBoost: {e}")
    
    def predict_proba(self, url: str) -> Dict[str, float]:
        """
        Предсказание вероятности фишинга
        
        Returns:
            Dict с вероятностями от каждой модели и ансамбля
        """
        # Извлекаем признаки
        features = extract_features(url)
        X = pd.DataFrame([features], columns=Config.FEATURE_COLS)
        
        result = {
            'random_forest': None,
            'xgboost': None,
            'ensemble': None
        }
        
        # Предсказания от каждой модели
        if self.random_forest is not None:
            try:
                rf_proba = self.random_forest.predict_proba(X)[0][1]
                result['random_forest'] = rf_proba
            except Exception as e:
                logger.error(f"Ошибка Random Forest: {e}")
        
        if self.xgboost is not None:
            try:
                xgb_proba = self.xgboost.predict_proba(X)[0][1]
                result['xgboost'] = xgb_proba
            except Exception as e:
                logger.error(f"Ошибка XGBoost: {e}")
        
        # Ансамбль (взвешенное среднее)
        valid_models = []
        weighted_sum = 0
        total_weight = 0
        
        if result['random_forest'] is not None:
            weighted_sum += result['random_forest'] * self.weights['random_forest']
            total_weight += self.weights['random_forest']
            valid_models.append('random_forest')
        
        if result['xgboost'] is not None:
            weighted_sum += result['xgboost'] * self.weights['xgboost']
            total_weight += self.weights['xgboost']
            valid_models.append('xgboost')
        
        if total_weight > 0:
            result['ensemble'] = weighted_sum / total_weight
        
        # Логирование
        logger.debug(f"URL: {url[:50]}... RF={result['random_forest']:.3f}, "
                    f"XGB={result['xgboost']:.3f}, Ensemble={result['ensemble']:.3f}")
        
        return result
    
    def predict(self, url: str) -> Tuple[int, float]:
        """
        Предсказание класса (0 - безопасно, 1 - опасно)
        
        Returns:
            (класс, вероятность)
        """
        result = self.predict_proba(url)
        proba = result['ensemble'] if result['ensemble'] is not None else 0.5
        return (1 if proba > 0.5 else 0, proba)
    
    def is_model_loaded(self) -> bool:
        """Проверка, загружена ли хотя бы одна модель"""
        return self.random_forest is not None or self.xgboost is not None

# Глобальный экземпляр
ensemble = EnsemblePredictor()
