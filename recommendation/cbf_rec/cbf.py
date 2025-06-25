import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import ast
from common.database import load_data
from sklearn.feature_extraction.text import TfidfVectorizer

class ProductRecommender:
    def __init__(self, base_product_id, compare_product_ids):
        self.base_product_id = base_product_id
        self.compare_product_ids = compare_product_ids
        self.vec_column = 'nutri'
        self.df = self.get_product_vector()
    
    def get_product_vector(self):
        all_ids = [self.base_product_id] + [pid for pid in self.compare_product_ids if pid != self.base_product_id]
        product_ids_str = ', '.join(str(pid) for pid in all_ids)
        query = f"""
        SELECT id, nutri
        FROM "Product_products"
        WHERE id IN ({product_ids_str})
        """
        df = load_data(query)

        return df

    def get_scores_for_product_ids(self):
        # base, compare product의 텍스트 추출
        base_row = self.df[self.df['id'] == self.base_product_id]
        base_text = base_row[self.vec_column].values[0]
        compare_texts = self.df[self.df['id'].isin(self.compare_product_ids)][self.vec_column].values

        # TF-IDF 벡터화
        vectorizer = TfidfVectorizer(
            min_df=1,  # 최소 문서 빈도
        )
        tfidf_matrix = vectorizer.fit_transform([base_text] + list(compare_texts))

        # base와 compare product 간 코사인 유사도 계산
        base_vec = tfidf_matrix[0]
        compare_vecs = tfidf_matrix[1:]
        scores = cosine_similarity(base_vec, compare_vecs)[0]

        result = [(pid, float(score)) for pid, score in zip(self.compare_product_ids, scores)]

        # 결과 반환
        return result
    
    def __call__(self):
        return self.get_scores_for_product_ids()
# 사용 예시:
# recommender = ProductRecommender(df)
# base_product_id = 123
# compare_product_ids = [101, 102, 103]
# scores = recommender.get_scores_for_product_ids(base_product_id, compare_product_ids)
# 결과: [(101, 0.98), (102, 0.87), (103, 0.92)]

# 기존 로직
# 1. tf-idf 함수의 입력값은 user_id와 product_id가 필요하다.
# 2. input으로 받은 user_id를 기반으로 db에서 Mypage_userlog를 조회해서 가장 마지막 purchase를 기준 상품으로 각 product_id의 tf-idf cosine유사도를 돌린다.
# 3. 돌려서 나온 product_id의 스코어를 return해주면 된다.

# 변경 로직
# 1. 민서님이 기준이되는 product_id를 주면 그 친구와 리스트로 넘어온 product_id를 코사인 유사도를 돌린다.
# 2. 튜플 형식(product_id, cosine similar score)으로 출력해서 넘겨주면 된다.
