from common.database import load_data, save_data_to_db
from common.popularity_calculate import steam_game_scores, min_max_scaler

def calculate_scores(df):
    """
    상품별로 popularity_score(정규화된 평점)를 계산해 id, title, popularity_score만 남긴 DataFrame를 반환하는 함수
    Args:
        df (pd.DataFrame): id, title, sentiment 컬럼을 가진 DataFrame
    Returns:
        pd.DataFrame: id, title, popularity_score 컬럼만 남긴 DataFrame
    """
    df['sentiment'] = df['sentiment'] == 'positive'
    df_star_rating = df.groupby('id').agg({'title': 'count', 'sentiment': 'sum'}).rename(columns={'title': 'TotalReviews', 'sentiment': 'PositiveReviews'})\
        .apply(lambda x: steam_game_scores(x['TotalReviews'], x['PositiveReviews']), axis=1).reset_index()
    df_star_rating['scaled_reviews_rating'] = min_max_scaler(df_star_rating['reviews_rating'].max(), df_star_rating['reviews_rating'].min(), df_star_rating['reviews_rating'])
    df = df[['id', 'title']].drop_duplicates()

    df_result = df.merge(
        df_star_rating[['id', 'scaled_reviews_rating']],
        on='id',
        how='left'
    ).rename(columns={'scaled_reviews_rating': 'popularity_score'})

    df_result['popularity_score'] = df_result['popularity_score'].fillna(0)

    return df_result

def main():
    """
    전체 파이프라인 실행 함수:
    1. 데이터 전처리
    2. 인기 점수 계산
    3. 데이터베이스에 점수 저장
    4. 상위 인기 상품 출력
    """
    # 상품과 리뷰 데이터를 id/product_id로 조인하여 필요한 컬럼만 조회
    query = '''
    SELECT p.id, p.title, r.sentiment
    FROM "Product_products" p
    INNER JOIN "Product_review" r
    ON p.id = r.product_id
    '''
    # 데이터 전처리 (상품-리뷰 조인)
    df = load_data(query)

    # 인기 점수 계산
    df = calculate_scores(df)

    # 데이터베이스에 점수 저장
    # 업데이트할 데이터 튜플 리스트 생성
    query = '''
    UPDATE "Product_products"
    SET popularity_score = %s
    WHERE id = %s
    '''
    data = [(row['popularity_score'], row['id']) for _, row in df.iterrows()]
    save_data_to_db(query, data)

    # 상위 인기 상품 출력
    print("Scores saved to DB:")
    print(df[['title', 'popularity_score']].sort_values(by='popularity_score', ascending=False).head())

if __name__ == "__main__":
    main()