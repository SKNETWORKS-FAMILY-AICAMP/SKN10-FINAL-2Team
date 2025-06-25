import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import ast

class ProductRecommender:
    def __init__(self, df, vec_column='pro_vec', id_column='id'):
        self.df = df
        self.vec_column = vec_column
        self.id_column = id_column
        # pro_vec 컬럼을 numpy array로 변환
        self.vec_matrix = np.vstack(self.df[self.vec_column].apply(lambda x: np.array(ast.literal_eval(x))))
        self.cosine_sim = cosine_similarity(self.vec_matrix, self.vec_matrix)

    def get_scores_for_product_ids(self, base_product_id, compare_product_ids):
        # 기준 상품의 인덱스 찾기
        try:
            base_index = self.df.index[self.df[self.id_column] == base_product_id][0]
        except IndexError:
            raise ValueError(f"기준 product_id {base_product_id}가 데이터프레임에 없습니다.")
        # 비교 대상 인덱스 찾기
        compare_indices = []
        compare_id_map = {}
        for pid in compare_product_ids:
            idxs = self.df.index[self.df[self.id_column] == pid].tolist()
            if idxs:
                compare_indices.append(idxs[0])
                compare_id_map[idxs[0]] = pid
        # 코사인 유사도 추출
        scores = []
        for idx in compare_indices:
            score = float(self.cosine_sim[base_index, idx])
            scores.append((compare_id_map[idx], score))
        return scores

# 1. tf-idf 함수의 입력값은 user_id와 product_id가 필요하다.
# 2. input으로 받은 user_id를 기반으로 db에서 Mypage_userlog를 조회해서 가장 마지막 purchase를 기준 상품으로 각 product_id의 tf-idf cosine유사도를 돌린다.
# 3. 돌려서 나온 product_id의 스코어를 return해주면 된다.