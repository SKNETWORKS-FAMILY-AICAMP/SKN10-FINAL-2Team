import os
import ast
import copy
import time
import boto3
import pickle
import logging
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from lightfm import LightFM
from lightfm.data import Dataset
from lightfm.evaluation import precision_at_k, recall_at_k, auc_score
from common.database import load_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def prepare_dataset(df_logs, df_products):
    """
    유저 로그와 상품 정보를 받아 LightFM 학습에 필요한 interaction matrix와 item feature matrix를 생성하는 함수

    Args:
        df_logs (pd.DataFrame): user_id, product_id, action 컬럼을 가진 유저 로그 데이터
        df_products (pd.DataFrame): product_id, title, ingredients, brand, supplement_type, product_form, vegan 컬럼을 가진 상품 정보 데이터

    Returns:
        tuple: (dataset, interaction_matrix, item_features)
            - dataset: LightFM Dataset 객체 (user/item 인덱스 매핑 정보 포함)
            - interaction_matrix: 상호작용 행렬 (user x item)
            - item_features: 아이템 feature 행렬
    """
    # 유저 행동별 가중치 설정
    action_weight = {
        'click': 1.0,
        'purchase': 5.0,
    }

    # 아이템 feature로 사용할 컬럼 지정
    item_feature_fields = ['brand', 'supplement_type', 'product_form', 'vegan']

    # 로그에 등장한 상품만 필터링
    used_product_ids = df_logs['product_id'].unique()
    df_products_used = df_products[df_products['product_id'].isin(used_product_ids)].copy()

    df_products_used['ingredients'] = df_products_used['ingredients'].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )

    all_ingredients_names = set()
    for row in df_products_used['ingredients']:
        for ing in row:
            all_ingredients_names.add(ing['ingredient_name'])
    
    # 모든 아이템 feature 값 추출
    all_item_features = np.unique(
        np.concatenate([
            df_products_used[item_feature_fields].values.ravel(),
            list(all_ingredients_names)
        ])
    )

    # LightFM Dataset 객체 생성 및 유저/아이템/아이템 feature fitting
    dataset = Dataset()
    dataset.fit(
        users=df_logs['user_id'].unique(),
        items=df_products_used['product_id'].unique(),
        item_features=all_item_features
    )

    # (user, item, weight) 튜플 생성
    interactions = [
        (row.user_id, row.product_id, action_weight.get(row.action, 1.0)) for _, row in df_logs.iterrows()
    ]
    # 상호작용 행렬 생성
    interaction_matrix, _ = dataset.build_interactions(interactions)

    # 아이템 feature 튜플 생성
    item_features_data = []
    for _, row in df_products_used.iterrows():
        base_features = [row[col] for col in item_feature_fields]

        ingredient_features = [ing['ingredient_name'] for ing in row['ingredients']]

        all_features = base_features + ingredient_features
        item_features_data.append((row['product_id'], all_features))
    # 아이템 feature 행렬 생성
    item_features = dataset.build_item_features(item_features_data)

    return dataset, interaction_matrix, item_features

def train_lightfm_model(interaction_matrix, item_features, epochs=10, num_threads=1):
    """
    interaction matrix와 item feature matrix를 받아 LightFM 모델을 학습하는 함수
    가장 높은 auc@10을 보인 모델을 반환한다.

    Args:
        interaction_matrix (scipy.sparse matrix): 유저-아이템 상호작용 행렬
        item_features (scipy.sparse matrix): 아이템 feature 행렬
        epochs (int): 학습 epoch 수
        num_threads (int): 학습에 사용할 스레드 수

    Returns:
        LightFM: auc@10이 가장 높았던 LightFM 모델 객체
    """
    try:
        model = LightFM(loss='warp')
        best_model = None
        best_auc = -1
        best_epoch = -1

        for epoch in range(epochs):
            model.fit_partial(interaction_matrix, item_features=item_features, epochs=1, num_threads=num_threads)
            auc = auc_score(model, interaction_matrix, item_features=item_features, num_threads=num_threads).mean()
            if auc > best_auc:
                best_auc = auc
                best_epoch = epoch
                best_model = copy.deepcopy(model)
            logging.info(f"Epoch {epoch+1}: auc@10={auc:.4f}")

        logging.info(f"Best auc@10: {best_auc:.4f} at epoch {best_epoch+1}")
        return best_model
    except Exception as e:
        logging.error("모델 학습 중 에러:", e)
        raise

def train_lightfm_with_metrics(interaction_matrix, item_features, epochs=10, num_threads=1, save_path='personalized/lightfm_metrics.png'):
    model = LightFM(loss='warp')
    precisions = []
    recalls = []
    aucs = []
    best_auc = -1
    best_epoch = -1
    best_model = None

    for epoch in range(epochs):
        model.fit_partial(interaction_matrix, item_features=item_features, epochs=1, num_threads=num_threads)
        precision = precision_at_k(model, interaction_matrix, item_features=item_features, k=10).mean()
        recall = recall_at_k(model, interaction_matrix, item_features=item_features, k=10).mean()
        auc = auc_score(model, interaction_matrix, item_features=item_features).mean()
        precisions.append(precision)
        recalls.append(recall)
        aucs.append(auc)
        if auc > best_auc:
            best_auc = auc
            best_epoch = epoch
            best_model = copy.deepcopy(model)
        logging.info(f"Epoch {epoch+1}: precision@10={precision:.4f}, recall@10={recall:.4f}, auc={auc:.4f}")

    # 그래프 저장
    plt.figure(figsize=(15, 5))

    plt.subplot(1,3,1)
    plt.plot(precisions, marker='o', color='g')
    plt.title('Precision@10')
    plt.xlabel('Epoch')
    plt.ylabel('Precision')

    plt.subplot(1,3,2)
    plt.plot(recalls, marker='o', color='r')
    plt.title('Recall@10')
    plt.xlabel('Epoch')
    plt.ylabel('Recall')

    plt.subplot(1,3,3)
    plt.plot(aucs, marker='o', color='b')
    plt.title('AUC')
    plt.xlabel('Epoch')
    plt.ylabel('AUC')

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    logging.info(f"학습 곡선 그래프가 {save_path}에 저장되었습니다.")
    logging.info(f"Best auc: {best_auc:.4f} at epoch {best_epoch+1}")

    return best_model

def save_model_to_s3(model, dataset, item_features, bucket, prefix='lightfm_model'):
    """
    학습된 모델, user/item 매핑 정보, item feature 정보를 S3에 저장하는 함수

    Args:
        model (LightFM): 학습된 LightFM 모델 객체
        dataset (Dataset): user/item 인덱스 매핑 정보가 포함된 Dataset 객체
        item_features (scipy.sparse matrix): 아이템 feature 행렬
        bucket (str): S3 버킷 이름
        prefix (str): S3 파일명 prefix
    """
    s3 = boto3.client('s3')

    def upload_pickle(obj, key):
        buffer = BytesIO()
        pickle.dump(obj, buffer)
        buffer.seek(0)
        s3.upload_fileobj(buffer, bucket, key)

    upload_pickle(model, f"{prefix}.pkl")
    upload_pickle(dataset, f"{prefix}_dataset.pkl")
    upload_pickle(item_features, f"{prefix}_item_features.pkl")
    logging.info(f"Model, dataset, item_features saved to s3://{bucket}/{prefix}*")

def main():
    """
    전체 추천 파이프라인을 실행하는 메인 함수.
    1. 데이터 로드
    2. 전처리 및 행렬 생성
    3. 모델 학습
    4. 모델 저장
    5. 평가 및 샘플 추천 결과 출력
    """
    logging.info("데이터 로드 시작")
    # 유저 로그 데이터 쿼리 및 로드
    log_query = """
    SELECT user_id, product_id, action
    FROM "Mypage_userlog"
    WHERE user_id IN (
        SELECT user_id
        FROM "Mypage_userlog"
        GROUP BY user_id
        HAVING COUNT(DISTINCT product_id) >= 5
        )
    """
    df_logs = load_data(log_query)
    
    # action 우선순위 컬럼 추가 (purchase=1, click=2)
    action_priority = {'purchase': 1, 'click': 2}
    df_logs['action_priority'] = df_logs['action'].map(action_priority).fillna(3)

    # user_id, product_id별로 action 우선순위로 정렬 후 중복 제거
    df_logs = df_logs.sort_values(['user_id', 'product_id', 'action_priority'], ascending=[True, True, True])
    df_logs = df_logs.drop_duplicates(subset=['user_id', 'product_id'], keep='first').reset_index(drop=True)

    df_logs = df_logs[['user_id', 'product_id', 'action']]

    # 상품 데이터 쿼리 및 로드
    product_query = """
    SELECT id as product_id, title, ingredients, brand, supplement_type, product_form, vegan
    FROM "Product_products"
    """
    df_products = load_data(product_query)
    logging.info("로그 유저 수: %d", df_logs['user_id'].nunique())
    logging.info("로그 상품 수: %d", df_logs['product_id'].nunique())
    logging.info("데이터 로드 완료")

    logging.info("데이터 전처리 시작")
    # 상호작용 행렬 및 매핑 정보 생성
    dataset, interaction_matrix, item_features = prepare_dataset(df_logs, df_products)
    logging.info("데이터 전처리 완료, 행렬 크기: %s", interaction_matrix.shape)

    # 모델 학습
    logging.info("모델 학습 시작")
    start = time.time()
    # model = train_lightfm_model(interaction_matrix, item_features, epochs=30)
    model = train_lightfm_with_metrics(interaction_matrix, item_features, epochs=30)
    logging.info("모델 학습 완료, 소요 시간: %.4f 초", time.time() - start)

    # 테스트 점수 출력 (precision@k, recall@k, auc)
    logging.info("모델 평가 시작")
    precision = precision_at_k(model, interaction_matrix, item_features=item_features, k=10).mean()
    recall = recall_at_k(model, interaction_matrix, item_features=item_features, k=10).mean()
    auc = auc_score(model, interaction_matrix, item_features=item_features).mean()
    logging.info("모델 평가 완료")

    # 모델 저장
    if precision > 0.4 and recall > 0.4:
        save_model_to_s3(model, dataset, item_features, bucket='lightfm-model', prefix='lightfm_model')
        logging.info("모델 저장 완료 (Precision: %.4f, Recall: %.4f, AUC: %.4f)", precision, recall, auc)
    else:
        logging.warning("모델 저장 조건 미충족 (Precision: %.4f, Recall: %.4f, AUC: %.4f)", precision, recall, auc)

if __name__ == "__main__":
    main()
