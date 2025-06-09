import pandas as pd
import numpy as np

def steam_game_scores(df):
    """
    각 상품(id)에 대해 긍정/부정 리뷰 수와 Steam 방식 평점(reviews_rating)을 계산하는 함수
    Args:
        df (pd.DataFrame): 특정 id에 해당하는 리뷰 DataFrame
    Returns:
        pd.Series: positive_reviews, negative_reviews, reviews_rating 컬럼을 가진 시리즈
    """
    # 긍정 리뷰 개수 계산
    PositiveReviews = (df['sentiment'] == 'positive').sum()
    # 부정 리뷰 개수 계산
    NegativeReviews = (df['sentiment'] == 'negative').sum()
    # 전체 리뷰 개수 계산
    TotalReviews = PositiveReviews + NegativeReviews

    # 리뷰가 없을 경우 0 반환
    if TotalReviews == 0:
        return pd.Series({'positive_reviews': 0, 'negative_reviews': 0, 'reviews_rating': 0})
    
    # 긍정 리뷰 비율
    ReviewScore = PositiveReviews / TotalReviews
    # Steam 방식 평점 계산
    Rating = ReviewScore - (ReviewScore - 0.5) * 2 ** (-np.log10(TotalReviews + 1))

    return pd.Series({'positive_reviews': PositiveReviews, 'negative_reviews': NegativeReviews, 'reviews_rating': Rating})

def get_popularity_scores(df):
    """
    전체 DataFrame에서 id별로 steam_game_scores를 적용하고, 평점을 0~1로 정규화하는 함수
    Args:
        df (pd.DataFrame): id, title, sentiment 컬럼을 가진 DataFrame
    Returns:
        pd.DataFrame: id별 positive_reviews, negative_reviews, reviews_rating, scaled_reviews_rating 컬럼을 가진 DataFrame
    """
    # id별로 steam_game_scores 적용
    df = df.groupby('id').apply(steam_game_scores).reset_index()

    # 평점 정규화 (0~1)
    max_rating = df['reviews_rating'].max()
    min_rating = df['reviews_rating'].min()
    df['scaled_reviews_rating'] = (df['reviews_rating'] - min_rating) / (max_rating - min_rating)

    return df

def calculate_scores(df):
    """
    상품별로 popularity_score(정규화된 평점)를 계산해 id, title, popularity_score만 남긴 DataFrame를 반환하는 함수
    Args:
        df (pd.DataFrame): id, title, sentiment 컬럼을 가진 DataFrame
    Returns:
        pd.DataFrame: id, title, popularity_score 컬럼만 남긴 DataFrame
    """
    df_star_rating = get_popularity_scores(df)
    df = df[['id', 'title']].drop_duplicates()

    df_result = df.merge(
        df_star_rating[['id', 'scaled_reviews_rating']],
        on='id',
        how='left'
    ).rename(columns={'scaled_reviews_rating': 'popularity_score'})

    df_result['popularity_score'] = df_result['popularity_score'].fillna(0)

    return df_result
