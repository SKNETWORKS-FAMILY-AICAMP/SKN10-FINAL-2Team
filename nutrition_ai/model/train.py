import pandas as pd
from model import model
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# 데이터 로드 (예시)
data = pd.read_csv('../data/processed_bayesian_scores.csv')

# 특성과 타겟 분리 (예시)
X = data.drop(['title', 'bayesian_score'], axis=1)
y = data['bayesian_score']

# 데이터 분할
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 모델 생성 및 학습
reg = model.get_model()
reg.fit(X_train, y_train)

# 예측 및 평가
preds = reg.predict(X_test)
mse = mean_squared_error(y_test, preds)
print(f'Test MSE: {mse:.4f}')

# 모델 저장 (예시)
import joblib
joblib.dump(reg, '../data/trained_model.pkl') 