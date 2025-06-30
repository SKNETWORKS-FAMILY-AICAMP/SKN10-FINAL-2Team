import logging
import numpy as np
import pandas as pd
from .common.database import load_data
from .personalized.lightfm_recommendation import LightFMRecommender
from .cbf_rec.cbf import ProductRecommender

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class TotalRecommender:
    def __init__(self, params):
        """
        TotalRecommender 클래스 초기화

        Args:
            params (dict): {
                "user_id": 추천을 받을 사용자 ID (int),
                "product_ids": 추천 대상 상품 ID 리스트 (list)
            }
        """
        self.user_id = params.get("user_id")
        self.product_ids = params.get("product_ids")
        self.score_column = 'score'
        
        self.recent_product_id = self._get_recent_product_id()

        self.personalized_recommender = LightFMRecommender()

        logger.info(f"TotalRecommender 초기화: user_id={self.user_id}, product_ids={self.product_ids}")
    
    def _get_recent_product_id(self):
        """
        DB에서 해당 user_id의 로그 이력이 존재하는지 확인
        Returns:
            bool: 로그 이력이 있으면 True, 없으면 False
        """
        query = f"""
        SELECT product_id
        FROM "Mypage_userlog"
        WHERE user_id = {self.user_id}
        ORDER BY
            CASE WHEN action = 'purchase' THEN 0 ELSE 1 END,
            timestamp DESC
        """
        product_id = load_data(query)
        if not product_id.empty:
            return int(product_id.iloc[0]['product_id'])
        return None

    def _normalize_score(self, df):
        """
        DataFrame의 score 컬럼을 0~1로 정규화한다.
        Args:
            df (pd.DataFrame): 점수 컬럼이 포함된 데이터프레임
        Returns:
            pd.DataFrame: 정규화된 score 컬럼을 가진 데이터프레임
        """
        logger.info("점수 정규화 시작")

        if df.empty:
            df[self.score_column] = []

            logger.warning("정규화 대상 데이터프레임이 비어 있습니다.")
            return df

        min_score = df[self.score_column].min()
        max_score = df[self.score_column].max()

        if max_score > min_score:
            df[self.score_column] = (df[self.score_column] - min_score) / (max_score - min_score) + 1
            logger.info("정규화 완료: min=%.4f, max=%.4f", min_score, max_score)
        else:
            df[self.score_column] = 1.0
            logger.info("모든 점수가 동일하여 1.0으로 설정됨")

        return df

    def _weighted_shuffle(self, df):
        """
        score 컬럼을 가중치로 사용해 DataFrame을 랜덤하게 섞는다.
        Args:
            df (pd.DataFrame): 점수 컬럼이 포함된 데이터프레임
        Returns:
            pd.DataFrame: 가중치 기반으로 랜덤하게 섞인 데이터프레임
        """
        logger.info("가중치 기반 랜덤 셔플 시작")
        probs = df[self.score_column].values
        probs = np.nan_to_num(probs, nan=0.0)
        nonzero_count = np.count_nonzero(probs)
        if probs.sum() > 0 and nonzero_count == len(df):
            alpha = 2
            probs = probs ** alpha
            probs = probs / probs.sum()
            idx = np.random.choice(df.index, size=len(df), replace=False, p=probs)

            logger.info("가중치 기반 랜덤 셔플 완료: nonzero_count=%d, total_count=%d", nonzero_count, len(df))
            return df.loc[idx].reset_index(drop=True)
        else:
            logger.info("가중치가 모두 0이거나 데이터가 부족하여 단순 랜덤 셔플")
            return df.sample(frac=1).reset_index(drop=True)

    def get_recommendations(self):
        """
        사용자 ID와 상품 ID 리스트를 받아 추천 점수를 계산한다.
        1. 상품에 대해 개인화된 추천 점수 계산
        2. 개인화된 추천 점수가 없는 상품에 대해 비개인화된 추천 점수(CBF) 계산
        3. user_id가 없는 경우, 인기도 기반 추천 점수 제공

        Returns:
            pd.DataFrame: 상품 ID와 추천 점수, 추천 타입을 포함하는 DataFrame
        """
        logger.info("추천 생성 시작")
        if not self.recent_product_id:
            logger.info("user_id 없음 → 인기도 기반 추천 사용")
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
            total_items_list = total_items_score['product_id'].tolist()
            recommend_type = "비개인화"

            logger.info("인기도 기반 추천 %d개 반환", len(total_items_score))
            return total_items_list, recommend_type

        # 개인화 추천 점수 계산
        logger.info(f"개인화 추천 시작: user_id={self.user_id}")
        personalized_items_score, non_personalized_items = self.personalized_recommender(self.user_id, self.product_ids)
        logger.info("개인화 추천 완료: %d개", len(personalized_items_score))

        personalized_items_score = pd.DataFrame(personalized_items_score, columns=['product_id', 'score'])
        personalized_items_score['type'] = 'Personalized'
        personalized_items_score = self._normalize_score(personalized_items_score)

        # 비개인화 추천 점수 계산 - CBF
        logger.info("비개인화 추천 시작: 최근 상품 ID=%s", self.recent_product_id)
        non_personalized_recommender = ProductRecommender(self.recent_product_id, non_personalized_items)
        non_personalized_items_score = non_personalized_recommender()
        logger.info("비개인화 추천 완료: %d개", len(non_personalized_items_score))

        non_personalized_items_score = pd.DataFrame(non_personalized_items_score, columns=['product_id', 'score'])
        non_personalized_items_score['type'] = 'CBF'
        non_personalized_items_score = self._normalize_score(non_personalized_items_score)

        # 추천 점수 합치기
        total_items_score = pd.concat([personalized_items_score, non_personalized_items_score], ignore_index=True)

        # 상품 랜덤 정렬 - 점수 기반
        total_items_score = self._weighted_shuffle(total_items_score)
        total_items_list = total_items_score['product_id'].tolist()

        recommend_type = "개인화"

        logger.info("최종 추천 리스트 생성 완료: %d개", len(total_items_list))
        return total_items_list, recommend_type

    def __call__(self):
        """
        객체를 함수처럼 호출하면 추천 결과 DataFrame을 반환한다.
        Returns:
            pd.DataFrame: 추천 결과
        """
        logger.info("TotalRecommender 호출: user_id=%s, product_ids=%s", self.user_id, self.product_ids)
        return self.get_recommendations()
