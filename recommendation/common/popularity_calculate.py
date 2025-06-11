import pandas as pd
import numpy as np

def steam_game_scores(TotalReviews, PositiveReviews):
    """
    각 상품(id)에 대해 긍정/부정 리뷰 수와 Steam 방식 평점(reviews_rating)을 계산하는 함수
    Args:
        df (pd.DataFrame): 특정 id에 해당하는 리뷰 DataFrame
    Returns:
        pd.Series: positive_reviews, negative_reviews, reviews_rating 컬럼을 가진 시리즈
    """
    # 리뷰가 없을 경우 0 반환
    if TotalReviews == 0:
        return pd.Series({'positive_reviews': 0, 'negative_reviews': 0, 'reviews_rating': 0})
    
    # 긍정 리뷰 비율
    ReviewScore = PositiveReviews / TotalReviews
    # Steam 방식 평점 계산
    Rating = ReviewScore - (ReviewScore - 0.5) * 2 ** (-np.log10(TotalReviews + 1))

    return pd.Series({'positive_reviews': PositiveReviews, 'negative_reviews': TotalReviews - PositiveReviews, 'reviews_rating': Rating})

def min_max_scaler(max_rating, min_rating, reviews_rating):
    """
    전체 DataFrame에서 id별로 steam_game_scores를 적용하고, 평점을 0~1로 정규화하는 함수
    Args:
        df (pd.DataFrame): id, title, sentiment 컬럼을 가진 DataFrame
    Returns:
        pd.DataFrame: id별 positive_reviews, negative_reviews, reviews_rating, scaled_reviews_rating 컬럼을 가진 DataFrame
    """
    return (reviews_rating - min_rating) / (max_rating - min_rating)
