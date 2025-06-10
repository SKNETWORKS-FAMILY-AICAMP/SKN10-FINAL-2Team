# 추천 시스템

<br/>

## 비개인화 추천 시스템

<br/>

### 1. 인기도 기반 추천 시스템
<br/>

<p align="center">
    <img src="https://github.com/user-attachments/assets/f777114d-4026-40ea-a38a-05aed93903a6" width="600"/>
    <br/>
    <em>상품별 리뷰 기반 인기 점수 산출 플로우</em>
</p>

<br/>

**0. 리뷰 데이터 LLM 평가**

- 기존 별점이 주관적일 수 있으므로, 리뷰 텍스트에 대해 LLM 기반 감성 분석을 수행하여 긍정/부정 분류

<p align="center">
    <img src="https://github.com/user-attachments/assets/295fdbbf-1511-44b0-a989-6f7ea1f4c969" width="600"/>
    <br/>
    <em>기존 별점별 긍정/부정 비율</em>
</p>

> 일부 4-5점 리뷰에도 부정적인 감성 존재

<br/>

**1. 데이터 추출**

- DB에서 상품 및 리뷰 데이터 추출
  - `products.id`, `products.title`, `review.sentiment`

<br/>

**2. 인기 점수 계산**

> 전체 리뷰 수 계산

$$
TotalReviews = PositiveReviews + NegativeReviews
$$

<br/>

> 긍정 리뷰 비율

$$
ReviewScore = \frac{PositiveReviews}{TotalReviews}
$$

<br/>

> 리뷰 수가 적을수록 기본값(0.5)에 수렴하는 보정 점수

$$
Rating = ReviewScore - (ReviewScore - 0.5) \times 2^{- \log_{10}(TotalReviews + 1)}
$$

<br/>

> 상품별 인기 점수 정규화 (Min-Max Scaling)
  
$$
popularity_score = \frac{score - min(score)}{max(score) - min(score)}
$$

<br/>

**3. DB 업데이트**

- 계산된 `popularity_score`를 `products` 테이블에 업데이트

<br/>
