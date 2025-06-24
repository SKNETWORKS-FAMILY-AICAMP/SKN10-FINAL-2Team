import numpy as np
import pandas as pd
from personalized.lightfm_recommendation import LightFMRecommender
from non_personalized.non_personalized_recommendation import NonPersonalizedRecommender

class TotalRecommender:
    def __init__(self, user_id, userlog_product_ids, top_k=10, cbf_csv_path='non_personalized/cbf_similar_items.csv'):
        """
        user_id: 추천 대상 사용자 ID
        userlog_product_ids: 최근 userlog에서 추출한 product_id 리스트
        top_k: 각 추천 방식별 추출 개수
        cbf_csv_path: CBF 유사 상품 csv 경로
        """
        self.user_id = user_id
        self.userlog_product_ids = userlog_product_ids
        self.top_k = top_k
        self.total_k = top_k * 3
        self.cbf_csv_path = cbf_csv_path

        # 비개인화 추천
        nonpersonalized = NonPersonalizedRecommender()
        nonpersonalized_result = nonpersonalized(target_product_ids=userlog_product_ids, top_k=top_k, csv_path=cbf_csv_path)
        self.popular_df = nonpersonalized_result['popular']
        self.cbf_df = nonpersonalized_result['cbf']

        # 개인화 추천
        personalized = LightFMRecommender()
        self.personalized_df = personalized(user_id=user_id, top_k=top_k)

    def recommend(self, n=None):
        # personalized_df가 None이거나 row가 0개면 비개인화만 사용
        if self.personalized_df is None or len(self.personalized_df) < 5:
            dfs = [self.popular_df, self.cbf_df]
        else:
            dfs = [self.personalized_df, self.popular_df, self.cbf_df]

        # 컬럼 맞추기 (product_id, score, type)
        dfs_fixed = []
        for df in dfs:
            temp = df.copy()
            if 'similar_product_id' in temp.columns:
                temp = temp.rename(columns={'similar_product_id': 'product_id', 'similarity': 'score'})
            if 'popularity_score' in temp.columns:
                temp = temp.rename(columns={'popularity_score': 'score'})
            temp = temp[['product_id', 'score', 'type']]
            dfs_fixed.append(temp)

        all_df = pd.concat(dfs_fixed, ignore_index=True)
        all_df = all_df.sort_values('score', ascending=False)
        all_df = all_df.drop_duplicates(subset='product_id', keep='first').reset_index(drop=True)

        if n is not None:
            all_df = all_df.head(n)
        return all_df

    def __call__(self, top_k=10, type_weights=None, random_state=None):
        """
        전체 추천 결과에서 type별 점수 정규화 후 가중치 곱해서 top_k개를 랜덤 추출
        type_weights: {'Personalized': 1.0, 'Popularity': 1.0, 'CBF': 1.0} 등
        """
        # 전체 추천 결과
        candidates = self.recommend()
        if type_weights is None:
            type_weights = {'Personalized': 1.0, 'Popularity': 1.0, 'CBF': 1.0}

        # type별 점수 정규화
        candidates = candidates.copy()
        candidates['norm_score'] = 0.0
        for t in candidates['type'].unique():
            mask = candidates['type'] == t
            scores = candidates.loc[mask, 'score']
            min_s, max_s = scores.min(), scores.max()
            if max_s > min_s:
                norm = (scores - min_s) / (max_s - min_s)
            else:
                norm = np.ones_like(scores)
            candidates.loc[mask, 'norm_score'] = norm

        # type별 가중치 곱
        candidates['final_prob'] = candidates.apply(
            lambda row: row['norm_score'] * type_weights.get(row['type'], 1.0) + 1e-6, axis=1
        )
        probs = candidates['final_prob'].values
        probs = probs / probs.sum()

        rng = np.random.default_rng(random_state)
        chosen_idx = rng.choice(len(candidates), size=min(top_k, len(candidates)), replace=False, p=probs)
        return candidates.iloc[chosen_idx].reset_index(drop=True)
