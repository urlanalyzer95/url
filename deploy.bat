@echo off
echo 🚀 Деплой XGBoost + Random Forest...
pip install xgboost==2.0.3
python src\create_feedback_dataset.py
python src\train_rf.py
python src\train_xgboost.py
echo ✅ Две модели готовы!
echo ml\model_rf.pkl + ml\model_xgboost.pkl
pause