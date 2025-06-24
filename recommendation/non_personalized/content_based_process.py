import pandas as pd
import numpy as np
import ast
from sklearn.metrics.pairwise import cosine_similarity
from common.database import load_data

def get_similar_items_by_ingredient(top_k=10, csv_path='non_personalized/cbf_similar_items.csv'):
    """
    모든 상품에 대해 성분+함량 기반 유사 상품 Top-N을 csv로 저장
    """
    query = """
        SELECT id as product_id, ingredients
        FROM "Product_products"
    """
    df = load_data(query)

    # ingredients 파싱
    if isinstance(df['ingredients'].iloc[0], str):
        df['ingredients'] = df['ingredients'].apply(lambda x: ast.literal_eval(x))

    # 전체 성분명 추출
    all_ingredients = set()
    for ings in df['ingredients']:
        for ing in ings:
            all_ingredients.add(ing['ingredient_name'])
    all_ingredients = sorted(list(all_ingredients))

    # 성분별 함량 벡터 생성
    def ingredient_vector(ings):
        vec = np.zeros(len(all_ingredients))
        name_to_idx = {name: i for i, name in enumerate(all_ingredients)}
        for ing in ings:
            idx = name_to_idx.get(ing['ingredient_name'])
            if idx is not None:
                vec[idx] = ing.get('amount', 0)
        return vec
    df['ingredient_vec'] = df['ingredients'].apply(ingredient_vector)
    ingredient_matrix = np.stack(df['ingredient_vec'].values)

    # 모든 상품에 대해 유사 상품 Top-N 추출
    rows = []
    for i, base_pid in enumerate(df['product_id']):
        cosine_sim = cosine_similarity([ingredient_matrix[i]], ingredient_matrix).flatten()
        # 자기 자신 제외
        cosine_sim[i] = -1
        top_indices = cosine_sim.argsort()[-top_k:][::-1]
        for idx in top_indices:
            rows.append({
                'base_product_id': base_pid,
                'similar_product_id': df.iloc[idx]['product_id'],
                'similarity': cosine_sim[idx]
            })

    result_df = pd.DataFrame(rows)
    result_df.to_csv(csv_path, index=False)
    print(f"CBF 유사 상품 Top-{top_k} csv 저장 완료: {csv_path}")
