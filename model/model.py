from sklearn.ensemble import RandomForestRegressor

def get_model():
    return RandomForestRegressor(n_estimators=100, random_state=42) 