import pandas as pd
import joblib

# 모델 및 데이터 로드
model = joblib.load('../data/trained_model.pkl')
data = pd.read_csv('../data/processed_bayesian_scores.csv')

# 예측 (예시)
X = data.drop(['title', 'bayesian_score'], axis=1)
preds = model.predict(X)

data['predicted_score'] = preds
print(data[['title', 'predicted_score']].head()) 