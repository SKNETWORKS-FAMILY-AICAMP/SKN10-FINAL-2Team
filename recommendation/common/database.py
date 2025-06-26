from dotenv import load_dotenv
import psycopg2
import os
import pandas as pd
from sqlalchemy import create_engine

# .env 파일에서 환경변수 로드
load_dotenv()

# 데이터베이스 접속 정보 설정
db_params = {
    'host': os.getenv('POSTGRES_HOST'),
    'port': '5432',
    'dbname': 'postgre',
    'user': 'postgres',
    'password': os.getenv('POSTGRES_PASSWORD'),
}

def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
    )

def load_data(query):
    """
    데이터베이스에서 상품과 리뷰 데이터를 조인하여 전처리된 DataFrame을 반환하는 함수
    Args:
        db_params (dict): 데이터베이스 연결 정보
    Returns:
        pd.DataFrame: id, title, sentiment 컬럼을 가진 DataFrame
    """
    # 데이터베이스 연결
    engine = get_engine()

    # 쿼리 결과를 DataFrame으로 변환
    df = pd.read_sql(query, engine)
    # 연결 종료
    engine.dispose()
    return df

def save_data_to_db(query, data):
    """
    DataFrame의 점수 컬럼을 데이터베이스의 해당 테이블에 업데이트하는 함수
    Args:
        df (pd.DataFrame): 업데이트할 DataFrame
        key_col (str): DB에서 WHERE 조건으로 사용할 컬럼명 (예: 'id')
        db_params (dict): 데이터베이스 접속 정보
        db_col (str): 데이터베이스에 업데이트할 컬럼명 (예: 'popularity_score')
        table_name (str): 업데이트할 테이블명 (기본값: "Product_products")
    """
    # 데이터베이스 연결
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()
    try:
        # executemany로 일괄 업데이트 쿼리 실행
        cur.executemany(
            query, data
        )
        # 변경사항 저장
        conn.commit()
    # 에러 발생 시 롤백 및 에러 메시지 출력
    except Exception as e:
        print("DB update error:", e)
        conn.rollback()
    # 연결 종료
    finally:
        cur.close()
        conn.close()
