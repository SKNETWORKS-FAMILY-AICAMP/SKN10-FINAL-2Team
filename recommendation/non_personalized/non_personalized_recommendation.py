import pandas as pd
from common.database import load_data

class NonPersonalizedRecommender:
    def recommend_popular(self, top_k=10):
        """
        인기 상품 추천 (popularity_score 기준)
        """
        query = f"""
            SELECT id as product_id, title, popularity_score
            FROM "Product_products"
            ORDER BY popularity_score DESC
            LIMIT {top_k}
        """
        df = load_data(query)
        df['type'] = 'Popularity'
        return df.reset_index(drop=True)

    def recommend_cbf(self, target_product_ids, top_k=10, csv_path='cbf_similar_items.csv'):
        """
        미리 저장된 cbf_similar_items.csv에서 기준 상품(target_product_ids)과 유사한 상품 추천
        """
        df = pd.read_csv(csv_path)
        # 여러 기준 상품에 대해 유사 상품 후보 추출
        candidates = df[df['base_product_id'].isin(target_product_ids)]
        # 자기 자신은 제외
        candidates = candidates[~candidates['similar_product_id'].isin(target_product_ids)]
        # 유사도 높은 순, 중복 제거
        candidates = candidates.sort_values('similarity', ascending=False)
        candidates = candidates.drop_duplicates('similar_product_id').head(top_k)
        candidates['type'] = 'CBF'
        return candidates.reset_index(drop=True)
    
    def __call__(self, target_product_ids, top_k=10, csv_path='cbf_similar_items.csv'):
        """
        비개인화 추천을 위한 메인 함수
        1. 인기 상품 추천
        2. CBF 기반 유사 상품 추천
        """
        popular_recommendations = self.recommend_popular(top_k)
        cbf_recommendations = self.recommend_cbf(target_product_ids, top_k, csv_path)

        # 인기 상품과 CBF 추천 결과 합치기
        return {
            'popular': popular_recommendations.reset_index(drop=True),
            'cbf': cbf_recommendations.reset_index(drop=True)
        }
