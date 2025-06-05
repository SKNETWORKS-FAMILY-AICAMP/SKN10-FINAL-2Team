import pandas as pd
import psycopg2

def preprocess_data(db_params):
    """
    데이터베이스에서 상품과 리뷰 데이터를 조인하여 전처리된 DataFrame을 반환하는 함수
    Args:
        db_params (dict): 데이터베이스 연결 정보
    Returns:
        pd.DataFrame: id, title, sentiment 컬럼을 가진 DataFrame
    """
    # 데이터베이스 연결
    conn = psycopg2.connect(**db_params)
    # 상품과 리뷰 데이터를 id/product_id로 조인하여 필요한 컬럼만 조회
    query = '''
    SELECT p.id, p.title, r.sentiment
    FROM "Product_products" p
    INNER JOIN "Product_review" r
    ON p.id = r.product_id
    '''
    # 쿼리 결과를 DataFrame으로 변환
    df = pd.read_sql(query, conn)
    # 연결 종료
    conn.close()
    return df
