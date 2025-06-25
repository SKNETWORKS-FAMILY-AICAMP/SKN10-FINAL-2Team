import numpy as np
import pandas as pd
from personalized.lightfm_recommendation import LightFMRecommender
from non_personalized.non_personalized_recommendation import NonPersonalizedRecommender

class TotalRecommender:
    def __init__(self, user_id=None, product_ids=[], top_k=10, cbf_csv_path='non_personalized/cbf_similar_items.csv'):
        """
        user_id: 추천 대상 사용자 ID
        userlog_product_ids: 최근 userlog에서 추출한 product_id 리스트
        top_k: 각 추천 방식별 추출 개수
        cbf_csv_path: CBF 유사 상품 csv 경로
        """
        self.random_state = None
        self.type_weights = {
            'Personalized': 5.0,
            'Popularity': 1.0,
            'CBF': 0.5
        }

        self.user_id = user_id
        self.product_ids = product_ids
        self.top_k = top_k
        self.total_k = top_k * 3
        self.cbf_csv_path = cbf_csv_path

        # 비개인화 추천
        self.nonpersonalized = NonPersonalizedRecommender(self.user_id, self.top_k, self.cbf_csv_path)
        nonpersonalized_result = self.nonpersonalized(target_product_ids=product_ids)
        self.popular_df = nonpersonalized_result['popular']
        self.cbf_df = nonpersonalized_result['cbf']

        # 개인화 추천
        self.personalized = LightFMRecommender()
        self.personalized_df = self.personalized(user_id=self.user_id, top_k=self.top_k)

    def recommend(self):
        # personalized_df가 None이거나 row가 0개면 비개인화만 사용
        if self.personalized_df is None or len(self.personalized_df) < 5:
            dfs = [self.popular_df, self.cbf_df]
        else:
            dfs = [self.personalized_df, self.popular_df, self.cbf_df]

        all_df = pd.concat(dfs, ignore_index=True)
        all_df = all_df.sort_values('score', ascending=False)

        return all_df
    
    def _get_product_scores(self):
        personalized_scores = dict(self.personalized.get_product_score(self.user_id, self.product_ids))
        popular_scores = self.nonpersonalized.get_product_scores(self.product_ids)
        nonpersonalized_scores = dict(zip(popular_scores['product_id'], popular_scores['popularity_score']))

        row = []
        for pid in self.product_ids:
            personalized_score = personalized_scores.get(pid, np.nan)
            nonpersonalized_score = nonpersonalized_scores.get(pid, np.nan)
            if not np.isnan(personalized_score):
                row.append({'product_id': pid, 'score': personalized_score, 'type': 'Personalized'})
            else:
                row.append({'product_id': pid, 'score': nonpersonalized_score, 'type': 'Popularity'})
        
        return pd.DataFrame(row)

    def __call__(self, mode='recommend'):
        """
        mode:
            'recommend' : 추천 pool에서 type별 점수 정규화+가중치로 top_k개 추출 (기본)
            'score'     : 입력 product_ids에 대해 get_product_scores로 점수 매칭 후 type별 가중치 랜덤 추출
        """
        if mode == 'score':
            if self.product_ids is None:
                raise ValueError("mode='score'일 때는 product_ids를 입력해야 합니다.")
            candidates = self._get_product_scores(self.product_ids)
        else:
            candidates = self.recommend()

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
            lambda row: row['norm_score'] * self.type_weights.get(row['type'], 1.0) + 1e-6, axis=1
        )
        probs = candidates['final_prob'].values
        probs = probs / probs.sum()

        rng = np.random.default_rng(self.random_state)
        chosen_idx = rng.choice(len(candidates), size=min(self.top_k, len(candidates)), replace=False, p=probs)
        return candidates.iloc[chosen_idx].reset_index(drop=True)
