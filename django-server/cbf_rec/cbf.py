import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import ast
from sklearn.feature_extraction.text import TfidfVectorizer

class ProductRecommender:
    def __init__(self, df, vec_column='nutri', id_column='id'):
        self.df = df
        self.vec_column = vec_column
        self.id_column = id_column
        self.id_to_index = {pid: idx for idx, pid in enumerate(self.df[self.id_column])}

    def get_scores_for_product_ids(self, base_product_id, compare_product_ids):
        # base, compare product의 텍스트 추출
        base_text = self.df.loc[self.df[self.id_column] == base_product_id, self.vec_column].values[0]
        compare_texts = self.df[self.df[self.id_column].isin(compare_product_ids)][self.vec_column].values

        # TF-IDF 벡터화
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([base_text] + list(compare_texts))

        # base와 compare product 간 코사인 유사도 계산
        base_vec = tfidf_matrix[0]
        compare_vecs = tfidf_matrix[1:]
        scores = cosine_similarity(base_vec, compare_vecs)[0]

        # 결과 반환
        return list(zip(compare_product_ids, scores))
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

