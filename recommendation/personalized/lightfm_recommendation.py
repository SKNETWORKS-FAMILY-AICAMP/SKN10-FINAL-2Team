import boto3
import pickle
import logging
import numpy as np
import pandas as pd
from io import BytesIO

class LightFMRecommender:
    """
    S3에 저장된 LightFM 모델을 불러와 사용자별 맞춤형 상품 추천 점수를 제공하는 클래스

    주요 기능:
    - S3에서 LightFM 모델, 데이터셋, 아이템 feature를 로드하여 메모리에 저장한다.
    - _get_product_score(user_id, product_ids): 특정 사용자와 상품 리스트에 대해 예측 점수를 반환한다.
    - __call__(user_id, product_ids): 객체를 함수처럼 호출하면 점수가 있는 상품과 nan인 상품을 분리해서 반환한다.

    사용 예시:
        recommender = LightFMRecommender()
        personalized_items, non_personalized_items = recommender(user_id=123, product_ids=[1,2,3])
    """
    def __init__(self):
        """
        S3 버킷에서 LightFM 모델, 데이터셋, 아이템 피처를 로드하여 객체 변수로 저장한다.
        """
        self.logger = logging.getLogger(__name__)
        self.bucket = "lightfm-model" # S3 버킷 이름
        self.prefix = "lightfm_model" # S3 파일 경로 접두사

        # S3에서 모델, 데이터셋, 아이템 피처를 각각 로드
        self.model = self._load_pickle_from_s3(f"{self.prefix}.pkl")
        self.dataset = self._load_pickle_from_s3(f"{self.prefix}_dataset.pkl")
        self.item_features = self._load_pickle_from_s3(f"{self.prefix}_item_features.pkl")

    def _load_pickle_from_s3(self, key):
        """
        S3에서 피클 파일을 다운로드하여 객체로 반환한다.

        Args:
            key (str): S3 내 파일 경로
        Returns:
            object: 피클로 저장된 객체
        """
        # S3 클라이언트 생성 및 파일 다운로드
        s3 = boto3.client('s3')
        buffer = BytesIO()
        s3.download_fileobj(self.bucket, key, buffer)
        buffer.seek(0)

        return pickle.load(buffer)
    
    def _get_user_idx(self, user_id):
        """
        주어진 user_id에 대한 내부 인덱스와 아이템 인덱스 맵을 반환한다.
        user_id가 없으면 None을 반환한다.

        Args:
            user_id (str or int): 사용자 ID

        Returns:
            tuple: (user_idx, item_id_map) 또는 None
        """
        user_id_map, _, item_id_map, _ = self.dataset.mapping()
        if user_id not in user_id_map:
            self.logger.error(f"User ID {user_id} not found.")
            return None
        user_idx = user_id_map[user_id]

        return user_idx, item_id_map

    def get_product_score(self, user_id, product_ids):
        """
        특정 user_id와 product_ids 리스트에 대해 LightFM score를 계산하여 반환한다.
        user_id 또는 product_id가 모델에 없으면 score를 np.nan으로 반환한다.

        Args:
            user_id (str or int): 사용자 ID
            product_ids (list): 점수를 계산할 상품 ID 리스트

        Returns:
            list of (product_id, score): 각 상품의 예측 점수 (없는 id는 np.nan)
        """
        result = self._get_user_idx(user_id)
        if result is None:
            return [(pid, np.nan) for pid in product_ids]
        user_idx, item_id_map = result

        scores = []
        for pid in product_ids:
            if pid in item_id_map:
                item_idx = item_id_map[pid]
                score = self.model.predict(user_idx, np.array([item_idx]), item_features=self.item_features)[0]
                scores.append((pid, float(score)))
            else:
                scores.append((pid, np.nan))

        return scores
    
    def __call__(self, user_id, product_ids):
        """
        객체를 함수처럼 호출하면 점수가 있는 상품과 nan인 상품을 분리해서 반환한다.

        Args:
            user_id (str or int): 추천을 받을 사용자 ID
            product_ids (list): 점수를 계산할 상품 ID 리스트

        Returns:
            tuple: (personalized_items, non_personalized_items)
                - personalized_items: [(product_id, score), ...] (score가 nan이 아닌 것)
                - non_personalized_items: [product_id, ...] (score가 nan인 것)
        """
        # 추천 상품 및 점수 쌍 추출
        product_score_pairs = self.get_product_score(user_id, product_ids)

        personalized_items_score = [(pid, score) for pid, score in product_score_pairs if not np.isnan(score)]
        non_personalized_items = [pid for pid, score in product_score_pairs if np.isnan(score)]

        return personalized_items_score, non_personalized_items
