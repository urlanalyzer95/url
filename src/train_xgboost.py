import pandas as pd
import joblib
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

print("🚀 ОБУЧЕНИЕ XGBOOST")

df_main = pd.read_csv('data/processed/url_dataset_features.csv')
try:
    df_fb = pd.read_csv('data/processed/feedback_xgboost.csv')
    df = pd.concat([df_main, df_fb]).drop_duplicates('url', keep='last')
    print(f"✅ Dataset 1+2: {len(df)} записей")
except:
    df = df_main
    print("⚠️ Только Dataset 1")

X = df.drop(['url','label'], axis=1)
y = df['label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model_xgb = xgb.XGBClassifier(n_estimators=200, learning_rate=0.1, max_depth=6, random_state=42)
model_xgb.fit(X_train, y_train)

accuracy = accuracy_score(y_test, model_xgb.predict(X_test))
print(f"✅ XGBoost точность: {accuracy:.2%}")

joblib.dump(model_xgb, 'ml/model_xgboost.pkl')
print("✅ XGBoost: ml/model_xgboost.pkl")