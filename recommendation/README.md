# 추천 시스템

<br/>

## 비개인화 추천 시스템

<br/>

### 1. 인기도 기반 추천 시스템
<br/>

<p align="center">
    <img src="https://github.com/user-attachments/assets/6ad3954d-1179-48f4-9c1c-d9a6be950dad" width="800"/>
    <br/>
    <em>상품별 리뷰 기반 인기 점수 산출 플로우</em>
</p>

<br/>

**1. 데이터 추출**

- DB의 상품 및 리뷰 테이블에서 필요한 데이터(products.id, products.title, review.sentiment) 추출

<br/>

**2. 인기 점수 계산**

> 전체 리뷰 수

$$
TotalReviews = PositiveReviews + NegativeReviews
$$

<br/>

> 긍정 리뷰 비율

$$
ReviewScore = \frac{PositiveReviews}{TotalReviews}
$$

<br/>

> 리뷰 수가 적을수록 기본 점수(0.5)에 수렴하는 보정 평점

$$
Rating = ReviewScore - (ReviewScore - 0.5) \times 2^{- \log_{10}(TotalReviews + 1)}
$$

<br/>

> 상품별 인기 점수 정규화(MinMaxScaling)
  
$$
popularity_score = \frac{score - min(score)}{max(score) - min(score)}
$$

<br/>

**3. DB 업데이트**

- DB의 상품 테이블에 인기 점수(products.popularity_score) 업데이트

<br/>
