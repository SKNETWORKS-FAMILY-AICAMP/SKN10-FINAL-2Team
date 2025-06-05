from popularity_data import preprocess_data
from popularity_score import calculate_scores
from dotenv import load_dotenv
import psycopg2
import os

# .env 파일에서 환경변수 로드
load_dotenv()

# 데이터베이스 접속 정보 설정
db_params = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def save_score_to_db(df, key_col, db_params, db_col, table_name="Product_products"):
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
        # 업데이트할 데이터 튜플 리스트 생성
        data = [(row[db_col], row[key_col]) for _, row in df.iterrows()]
        # executemany로 일괄 업데이트 쿼리 실행
        cur.executemany(
            f'UPDATE "{table_name}" SET {db_col} = %s WHERE {key_col} = %s',
            data
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

def main():
    """
    전체 파이프라인 실행 함수:
    1. 데이터 전처리
    2. 인기 점수 계산
    3. 데이터베이스에 점수 저장
    4. 상위 인기 상품 출력
    """
    # 데이터 전처리 (상품-리뷰 조인)
    df = preprocess_data(db_params)

    # 인기 점수 계산
    df = calculate_scores(df)

    # 데이터베이스에 점수 저장
    save_score_to_db(df, 'id', db_params, 'popularity_score', table_name="Product_products")

    # 상위 인기 상품 출력
    print("Scores saved to DB:")
    print(df[['title', 'popularity_score']].sort_values(by='popularity_score', ascending=False).head())

if __name__ == "__main__":
    main()
