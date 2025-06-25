import boto3
import pickle
import logging
import numpy as np
import pandas as pd
from io import BytesIO

class LightFMRecommender:
    """
    S3에 저장된 LightFM 모델을 불러와 사용자별 맞춤형 상품 추천을 제공하는 클래스

    주요 기능:
    - S3에서 LightFM 모델, 데이터셋, 아이템 feature를 로드하여 메모리에 저장한다.
    - recommend(user_id, top_k): 특정 사용자에게 top_k개의 추천 상품 ID와 점수를 반환한다.
    - get_product_score(user_id, product_ids): 특정 사용자와 상품 리스트에 대해 예측 점수를 반환한다.
    - _get_product_info(product_score_pairs): 추천 상품 ID와 점수 쌍을 받아 상품 정보와 점수를 포함한 DataFrame을 반환한다.
    - __call__(user_id, top_k): 객체를 함수처럼 호출하면 추천 결과 DataFrame을 바로 반환한다.

    사용 예시:
        recommender = LightFMRecommender()
        recommendations = recommender(user_id=123, top_k=5)
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
            tuple: (user_idx, item_id_map)
        """
        user_id_map, _, item_id_map, _ = self.dataset.mapping()
        if user_id not in user_id_map:
            self.logger.error(f"User ID {user_id} not found.")
            return None
        user_idx = user_id_map[user_id]

        return user_idx, item_id_map

    def recommend(self, user_id, top_k=5):
        """
        입력한 user_id에 대해 top_k개의 추천 상품 ID와 점수를 반환한다.
        존재하지 않는 사용자일 경우 빈 리스트를 반환한다.

        Args:
            user_id (str or int): 추천을 받을 사용자 ID
            top_k (int): 추천할 상품 개수

        Returns:
            list of (product_id, score): 추천 상품 ID와 점수 쌍 리스트
        """
        # 데이터셋에서 매핑 정보 추출
        user_idx, item_id_map = self._get_user_idx(user_id)

        # 아이템 인덱스 정렬 (LightFM의 내부 인덱스와 일치시키기 위함)
        sorted_items = sorted(item_id_map.items(), key=lambda x: x[1])
        item_idxs = np.array([idx for _, idx in sorted_items])
        # 인덱스에서 실제 product_id로 역변환할 맵 생성
        reverse_item_index_map = {idx: iid for iid, idx in item_id_map.items()}

        # 추천 점수 예측
        scores = self.model.predict(user_idx, item_idxs, item_features=self.item_features)
        # 점수 내림차순으로 상위 top_k 인덱스 추출
        top_indices = np.argsort(-scores)[:top_k]
        # 추천 상품의 실제 product_id 추출
        top_item_ids = [reverse_item_index_map[i] for i in item_idxs[top_indices]]
        # 추천 점수 추출
        top_scores = [float(scores[i]) for i in top_indices]

        return list(zip(top_item_ids, top_scores))

    def get_product_score(self, user_id, product_ids):
        """
        특정 user_id와 product_ids 리스트에 대해 LightFM score를 계산하여 반환한다.
        모델에 없는 id는 score를 np.nan으로 반환한다.

        Args:
            user_id (str or int): 사용자 ID
            product_ids (list): 점수를 계산할 상품 ID 리스트

        Returns:
            list of (product_id, score): 각 상품의 예측 점수 (없는 id는 np.nan)
        """
        user_idx, item_id_map = self._get_user_idx(user_id)

        scores = []
        for pid in product_ids:
            if pid in item_id_map:
                item_idx = item_id_map[pid]
                score = self.model.predict(user_idx, np.array([item_idx]), item_features=self.item_features)[0]
                scores.append((pid, abs(float(score))))
            else:
                scores.append((pid, np.nan))

        return scores

    def _get_product_info(self, product_score_pairs):
        """
        추천 상품 ID와 점수 쌍을 받아 상품 정보(title 등)와 점수를 포함한 DataFrame을 반환한다.
        추천 결과가 없으면 빈 DataFrame을 반환한다.

        Args:
            product_score_pairs (list): (product_id, score) 쌍 리스트

        Returns:
            pd.DataFrame: 추천 상품 정보와 점수, 타입 컬럼 포함
        """
        if not product_score_pairs:
            print("Personalized recommendations are not available.")
            return pd.DataFrame(columns=["product_id", "type"])
        
        df_product_info = pd.DataFrame(product_score_pairs, columns=["product_id", "score"])
        df_product_info["type"] = "Personalized"
        df_product_info = df_product_info.sort_values(by="score", ascending=False).reset_index(drop=True)

        return df_product_info
    
    def __call__(self, user_id, top_k=5):
        """
        객체를 함수처럼 호출하면 추천 결과 DataFrame을 바로 반환한다.

        Args:
            user_id (str or int): 추천을 받을 사용자 ID
            top_k (int): 추천할 상품 개수

        Returns:
            pd.DataFrame: 추천 상품 정보와 점수, 타입 컬럼 포함
        """
        # 추천 상품 및 점수 쌍 추출
        product_score_pairs = self.recommend(user_id, top_k=top_k)

        return self._get_product_info(product_score_pairs)
