import os
import ast
import copy
import time
import boto3
import pickle
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from lightfm import LightFM
from lightfm.data import Dataset
from scipy.sparse import lil_matrix
from lightfm.cross_validation import random_train_test_split
from lightfm.evaluation import precision_at_k, recall_at_k, auc_score
from common.database import load_data

# 로깅 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# 하이퍼파라미터 및 설정
EPOCHS = 30
NUM_THREADS = 1
SAVE_CONDITION = {'auc': 0.6}
S3_BUCKET = 'lightfm-model'
S3_PREFIX = 'lightfm_model'
METRICS_PATH = 'personalized/output/lightfm_metrics_final.png'

def load_logs():
    """
    유저 로그 데이터베이스에서 user_id, product_id, action 컬럼을 쿼리하여
    행동 우선순위에 따라 중복을 제거한 후 DataFrame으로 반환한다.
    - purchase > click 순으로 우선순위를 두고, 한 유저가 한 상품에 여러 행동을 했을 때 가장 높은 행동만 남긴다.
    - 최소 5개 이상의 상품에 대한 로그가 있는 유저만 포함한다.

    Returns:
        pd.DataFrame: user_id, product_id, action 컬럼을 가진 유저 로그 데이터
    """
    query = """
    SELECT user_id, product_id, action
    FROM "Mypage_userlog"
    WHERE user_id IN (
        SELECT user_id
        FROM "Mypage_userlog"
        GROUP BY user_id
        HAVING COUNT(product_id) >= 5
        )
    """
    df = load_data(query)
    action_priority = {'purchase': 1, 'click': 2}
    df['action_priority'] = df['action'].map(action_priority).fillna(3)
    df = df.sort_values(['user_id', 'product_id', 'action_priority'])
    df = df.drop_duplicates(subset=['user_id', 'product_id'], keep='first')
    df = df[['user_id', 'product_id', 'action']]
    return df

def load_products():
    """
    상품 정보 데이터베이스에서 주요 컬럼을 쿼리하여 ingredients 컬럼을 리스트로 변환한 후 DataFrame으로 반환한다.
    - ingredients 컬럼은 문자열로 저장되어 있으므로 ast.literal_eval로 파싱하여 리스트로 변환한다.

    Returns:
        pd.DataFrame: product_id, title, ingredients, brand, supplement_type, product_form, vegan 컬럼을 가진 상품 정보 데이터
    """
    query = """
    SELECT id as product_id, title, ingredients, brand, supplement_type, product_form, vegan
    FROM "Product_products"
    """
    df = load_data(query)
    df['ingredients'] = df['ingredients'].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else []
    )
    return df

def prepare_dataset(df_logs, df_products):
    """
    유저 로그와 상품 정보를 바탕으로 LightFM 학습에 필요한 interaction matrix와 item feature matrix를 생성한다.
    - 유저가 같은 상품에 여러 번 상호작용한 경우 행동별 가중치를 합산하여 반영한다.

    Args:
        df_logs (pd.DataFrame): user_id, product_id, action 컬럼을 가진 유저 로그 데이터
        df_products (pd.DataFrame): product_id, title, ingredients, brand, supplement_type, product_form, vegan 컬럼을 가진 상품 정보 데이터

    Returns:
        tuple: (dataset, interaction_matrix, item_features, interactions)
            - dataset: LightFM Dataset 객체 (user/item 인덱스 매핑 정보 포함)
            - interaction_matrix: 상호작용 행렬 (user x item)
            - item_features: 아이템 feature 행렬
            - interactions: (user_id, product_id, weight) 튜플 리스트
    """
    # 유저 행동별 가중치 설정
    action_weight = {
        'click': 1.0,
        'purchase': 5.0,
    }

    # (1) 상품 필터링 (로그에 등장한 상품만)
    used_product_ids = df_logs['product_id'].unique()
    df_products_used = df_products[df_products['product_id'].isin(used_product_ids)].copy()

    # (2) 아이템 feature 추출용 ingredients 정제
    df_products_used['ingredients'] = df_products_used['ingredients'].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )

    all_ingredients_names = {
        ing['ingredient_name']
        for ingredients in df_products_used['ingredients']
        for ing in ingredients
        if 'ingredient_name' in ing
    }

    item_feature_fields = ['brand', 'supplement_type', 'product_form', 'vegan']
    all_item_features = np.unique(
        np.concatenate([
            df_products_used[item_feature_fields].values.ravel(),
            list(all_ingredients_names)
        ])
    )

    # (3) Dataset fitting
    dataset = Dataset()
    dataset.fit(
        users=df_logs['user_id'].unique(),
        items=df_products_used['product_id'].unique(),
        item_features=all_item_features
    )

    # (4) 행동 가중치 적용 및 집계
    df_logs['weight'] = df_logs['action'].map(action_weight).fillna(0)
    df_agg = df_logs.groupby(['user_id', 'product_id'])['weight'].sum().reset_index()

    interactions = list(df_agg.itertuples(index=False, name=None))  # (user_id, product_id, weight)
    interaction_matrix, _ = dataset.build_interactions(interactions)

    # (5) 아이템 feature 구성
    item_features_data = []
    for _, row in df_products_used.iterrows():
        features = [row[col] for col in item_feature_fields if pd.notna(row[col])]
        features += [ing['ingredient_name'] for ing in row['ingredients'] if 'ingredient_name' in ing]
        item_features_data.append((row['product_id'], features))

    item_features = dataset.build_item_features(item_features_data)

    return dataset, interaction_matrix, item_features, interactions

def train_test_split(interaction_matrix, test_percentage=0.2, random_state=42):
    np.random.seed(random_state)
    matrix = interaction_matrix.tolil()
    num_users, _ = matrix.shape

    train = lil_matrix(matrix.shape)
    test = lil_matrix(matrix.shape)

    for user in range(num_users):
        item_indices = matrix.rows[user]
        if len(item_indices) == 0:
            continue

        test_size = max(1, int(len(item_indices) * test_percentage))
        test_items = np.random.choice(item_indices, size=test_size, replace=False)

        for item in item_indices:
            if item in test_items:
                test[user, item] = matrix[user, item]
            else:
                train[user, item] = matrix[user, item]
    
    return train.tocsr(), test.tocsr()

def train_lightfm_model(train_interaction_matrix, test_interaction_matrix, item_features, epochs, num_threads, save_plot_path=None):
    """
    interaction matrix와 item feature matrix를 받아 LightFM 모델을 학습하는 함수
    - 각 epoch마다 precision@10, recall@10, auc@10을 평가한다.
    - 가장 높은 auc@10을 보인 모델을 반환한다.
    - 학습 곡선(precision/recall/auc)을 저장할 수 있다.

    Args:
        interaction_matrix (scipy.sparse matrix): 유저-아이템 상호작용 행렬
        item_features (scipy.sparse matrix): 아이템 feature 행렬
        epochs (int): 학습 epoch 수
        num_threads (int): 학습에 사용할 스레드 수
        save_plot_path (str, optional): 학습 곡선 저장 경로

    Returns:
        tuple: (best_model, last_precision, last_recall, last_auc)
            - best_model: auc@10이 가장 높았던 LightFM 모델 객체
            - last_precision: 마지막 epoch의 precision@10
            - last_recall: 마지막 epoch의 recall@10
            - last_auc: 마지막 epoch의 auc@10
    """
    model = LightFM(loss='warp')
    best_model = None
    best_auc = -1
    best_epoch = -1

    precisions, recalls, aucs = [], [], []

    for epoch in range(epochs):
        model.fit_partial(train_interaction_matrix, item_features=item_features, epochs=1, num_threads=num_threads)
        precision = precision_at_k(model, test_interaction_matrix, train_interaction_matrix, item_features=item_features, k=10).mean()
        recall = recall_at_k(model, test_interaction_matrix, train_interaction_matrix, item_features=item_features, k=10).mean()
        auc = auc_score(model, test_interaction_matrix, train_interaction_matrix, item_features=item_features, num_threads=num_threads).mean()

        precisions.append(precision)
        recalls.append(recall)
        aucs.append(auc)

        if auc > best_auc:
            best_auc = auc
            best_epoch = epoch
            best_model = copy.deepcopy(model)
        
        logger.info(f"Epoch {epoch+1}: precision@10={precision:.4f}, recall@10={recall:.4f}, auc={auc:.4f}")

    logger.info(f"Best auc@10: {best_auc:.4f} at epoch {best_epoch+1}")

    # if save_plot_path:
    #     os.makedirs(os.path.dirname(save_plot_path), exist_ok=True)
    #     plt.figure(figsize=(15, 5))

    #     metrics = [
    #         ("Precision@10", precisions),
    #         ("Recall@10", recalls),
    #         ("AUC", aucs),
    #     ]

    #     for i, (metric_name, values) in enumerate(metrics):
    #         plt.subplot(1, 3, i + 1)
    #         plt.plot(values, marker='o')
    #         plt.title(metric_name)
    #         plt.xlabel('Epoch')
    #         plt.ylabel(metric_name)
    #     plt.tight_layout()
    #     plt.savefig(save_plot_path)
    #     plt.close()
    #     logger.info(f"학습 곡선 그래프 저장됨: {save_plot_path}")

    return best_model, precisions[-1], recalls[-1], aucs[-1]

def upload_pickle_to_s3(obj, bucket, key):
    """
    객체를 pickle로 직렬화하여 S3에 업로드

    Args:
        obj (object): 저장할 객체
        bucket (str): S3 버킷 이름
        key (str): S3 파일 경로
    """
    s3 = boto3.client('s3')
    buffer = BytesIO()
    pickle.dump(obj, buffer)
    buffer.seek(0)
    s3.upload_fileobj(buffer, bucket, key)

def save_model_to_s3(model, dataset, item_features, bucket, prefix):
    """
    학습된 모델, user/item 매핑 정보, item feature 정보를 S3에 저장하는 함수

    Args:
        model (LightFM): 학습된 LightFM 모델 객체
        dataset (Dataset): user/item 인덱스 매핑 정보가 포함된 Dataset 객체
        item_features (scipy.sparse matrix): 아이템 feature 행렬
        bucket (str): S3 버킷 이름
        prefix (str): S3 파일명 prefix
    """
    upload_pickle_to_s3(model, bucket, f"{prefix}.pkl")
    upload_pickle_to_s3(dataset, bucket, f"{prefix}_dataset.pkl")
    upload_pickle_to_s3(item_features, bucket, f"{prefix}_item_features.pkl")
    logger.info(f"Model, dataset, item_features saved to s3://{bucket}/{prefix}*")

def main():
    """
    전체 추천 파이프라인을 실행하는 메인 함수
    1. 데이터 로드
    2. 전처리 및 행렬 생성
    3. 모델 학습
    4. 모델 저장 (조건 충족 시)
    5. 평가 결과 출력
    """
    logger.info("데이터 로드")
    df_logs = load_logs()
    df_products = load_products()
    logger.info(f"유저 수: {df_logs['user_id'].nunique()}, 상품 수: {df_logs['product_id'].nunique()}")

    logger.info("데이터 전처리 및 행렬 생성")
    dataset, interaction_matrix, item_features, interactions = prepare_dataset(df_logs, df_products)

    logger.info("학습 및 테스트 데이터 분할")
    train_interaction_matrix, test_interaction_matrix = train_test_split(interaction_matrix, test_percentage=0.2, random_state=42)

    logger.info("모델 학습 시작")
    start_time = time.time()
    model, precision, recall, auc = train_lightfm_model(
        train_interaction_matrix,
        test_interaction_matrix,
        item_features,
        epochs=EPOCHS,
        num_threads=NUM_THREADS,
        save_plot_path=METRICS_PATH
    )
    elapsed = time.time() - start_time
    logger.info(f"모델 학습 완료 (소요 시간: {elapsed:.2f}초)")

    logger.info("최종 평가 - Precision: %.4f, Recall: %.4f, AUC: %.4f", precision, recall, auc)

    # 모델 저장
    if auc > SAVE_CONDITION['auc']:
        save_model_to_s3(model, dataset, item_features, bucket=S3_BUCKET, prefix=S3_PREFIX)
        logger.info("모델 저장 완료")
    else:
        logger.warning("저장 조건 미충족으로 모델 저장되지 않음")

if __name__ == "__main__":
    main()
