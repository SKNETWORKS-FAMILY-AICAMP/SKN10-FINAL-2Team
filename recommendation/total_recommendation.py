import numpy as np
import pandas as pd
from common.database import load_data
from personalized.lightfm_recommendation import LightFMRecommender

class TotalRecommender:
    def __init__(self, user_id=None, product_ids=[]):
        """
        TotalRecommender 클래스 초기화
        Args:
            user_id (int, optional): 추천을 받을 사용자 ID
            product_ids (list, optional): 추천 대상 상품 ID 리스트
        """
        self.user_id = user_id
        self.product_ids = product_ids
        self.score_column = 'score'

        self.personalized_recommender = LightFMRecommender()

    def _normalize_score(self, df):
        """
        DataFrame의 score 컬럼을 0~1로 정규화한다.
        Args:
            df (pd.DataFrame): 점수 컬럼이 포함된 데이터프레임
        Returns:
            pd.DataFrame: 정규화된 score 컬럼을 가진 데이터프레임
        """
        if df.empty:
            df[self.score_column] = []
            return df
        
        min_score = df[self.score_column].min()
        max_score = df[self.score_column].max()
        
        if max_score > min_score:
            df[self.score_column] = (df[self.score_column] - min_score) / (max_score - min_score)
        else:
            df[self.score_column] = 1.0
        
        return df
    
    def _weighted_shuffle(self, df):
        """
        score 컬럼을 가중치로 사용해 DataFrame을 랜덤하게 섞는다.
        Args:
            df (pd.DataFrame): 점수 컬럼이 포함된 데이터프레임
        Returns:
            pd.DataFrame: 가중치 기반으로 랜덤하게 섞인 데이터프레임
        """
        probs = df[self.score_column].values
        probs = np.nan_to_num(probs, nan=0.0)
        nonzero_count = np.count_nonzero(probs)
        if probs.sum() > 0 and nonzero_count > len(df):
            probs = probs / probs.sum()
            idx = np.random.choice(df.index, size=len(df), replace=False, p=probs)
            return df.loc[idx].reset_index(drop=True)
        else:
            return df.sample(frac=1).reset_index(drop=True)

    def _get_recommendations(self):
        """
        사용자 ID와 상품 ID 리스트를 받아 추천 점수를 계산한다.
        1. 상품에 대해 개인화된 추천 점수 계산
        2. 개인화된 추천 점수가 없는 상품에 대해 비개인화된 추천 점수(CBF) 계산
        3. user_id가 없는 경우, 인기도 기반 추천 점수 제공

        Returns:
            pd.DataFrame: 상품 ID와 추천 점수, 추천 타입을 포함하는 DataFrame
        """
        if not self.user_id:
            # user_id가 없는 경우, 인기도 기반 추천 점수 제공
            product_ids_str = ', '.join(str(pid) for pid in self.product_ids)
            query = f"""
            SELECT id as product_id, popularity_score as score
            FROM "Product_products"
            WHERE id IN ({product_ids_str})
            """
            total_items_score = load_data(query)
            total_items_score['type'] = 'Popularity'
            total_items_score = self._weighted_shuffle(total_items_score)
            return total_items_score
        
        # 개인화 추천 점수 계산
        personalized_items_score, non_personalized_items = self.personalized_recommender(self.user_id, self.product_ids)
        personalized_items_score = pd.DataFrame(personalized_items_score, columns=['product_id', 'score'])
        personalized_items_score['type'] = 'Personalized'
        personalized_items_score = self._normalize_score(personalized_items_score)

        # 비개인화 추천 점수 계산 - CBF
        rng = np.random.default_rng()
        non_personalized_items_score = [(pid, rng.uniform(0, 1)) for pid in non_personalized_items]
        non_personalized_items_score = pd.DataFrame(non_personalized_items_score, columns=['product_id', 'score'])
        non_personalized_items_score['type'] = 'CBF'
        non_personalized_items_score = self._normalize_score(non_personalized_items_score)

        # 추천 점수 합치기
        total_items_score = pd.concat([personalized_items_score, non_personalized_items_score], ignore_index=True)

        # 상품 랜덤 정렬 - 점수 기반
        total_items_score = self._weighted_shuffle(total_items_score)
        total_items_list = total_items_score['product_id'].tolist()

        return total_items_list

    def __call__(self):
        """
        객체를 함수처럼 호출하면 추천 결과 DataFrame을 반환한다.
        Returns:
            pd.DataFrame: 추천 결과
        """
        return self._get_recommendations()
