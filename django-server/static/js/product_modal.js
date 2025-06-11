/**
 * 상품 상세 관련 JavaScript 유틸리티 함수
 * Product detail modal functionality
 */

// 상품 정보 캐시
let productDetailsCache = {};
// 좋아요 상태 캐시
let likedProductsCache = {};

/**
 * 상품 좋아요 토글 함수
 * @param {Event} event - 클릭 이벤트
 * @param {number|string} productId - 상품 ID
 */
function toggleLike(event, productId) {
    // 이벤트 버블링 방지
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    
    // productId가 문자열로 전달된 경우 숫자로 변환
    productId = parseInt(productId);
    
    console.log('좋아요 토글:', productId);
    
    // 좋아요 버튼 요소 찾기
    const likeButton = event.currentTarget;
    const heartIcon = likeButton.querySelector('.material-icons');
    
    // 현재 좋아요 상태
    const isCurrentlyLiked = heartIcon.classList.contains('text-red-500');
    const newLikedState = !isCurrentlyLiked;
    
    // API 요청 URL 및 메서드 설정
    const url = '/mypage/api/like/';
    const method = isCurrentlyLiked ? 'DELETE' : 'POST';
    
    // API 요청 전 UI 먼저 업데이트 (즉각적인 피드백)
    if (isCurrentlyLiked) {
        heartIcon.classList.remove('text-red-500');
        heartIcon.classList.add('text-gray-400');
    } else {
        heartIcon.classList.remove('text-gray-400');
        heartIcon.classList.add('text-red-500');
    }
    
    // 캐시 업데이트
    likedProductsCache[productId] = newLikedState;
    
    // 상품 정보 캐시에도 좋아요 상태 업데이트
    if (productDetailsCache[productId]) {
        productDetailsCache[productId].is_liked = newLikedState;
    }
    
    // 모달에 있는 좋아요 버튼도 업데이트
    updateAllLikeButtonsForProduct(productId, newLikedState);
    
    // API 요청
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),  // CSRF 토큰 필요
        },
        body: JSON.stringify({
            product_id: productId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('좋아요 처리 중 오류가 발생했습니다.');
        }
        return response.json();
    })
    .then(data => {
        console.log('좋아요 상태 변경됨:', data);
        // API 응답 기반으로 캐시 최종 업데이트
        likedProductsCache[productId] = data.is_liked;
        
        // 상품 정보 캐시에도 업데이트
        if (productDetailsCache[productId]) {
            productDetailsCache[productId].is_liked = data.is_liked;
        }
        
        // 모든 UI 요소 업데이트 (API 결과가 예상과 다를 경우 대비)
        if (data.is_liked !== newLikedState) {
            updateAllLikeButtonsForProduct(productId, data.is_liked);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // 오류 발생 시 원래 상태로 되돌림
        likedProductsCache[productId] = isCurrentlyLiked;
        
        // 상품 정보 캐시도 되돌림
        if (productDetailsCache[productId]) {
            productDetailsCache[productId].is_liked = isCurrentlyLiked;
        }
        
        // 모든 버튼 원래 상태로 되돌리기
        updateAllLikeButtonsForProduct(productId, isCurrentlyLiked);
    });
}

/**
 * 특정 상품에 대한 모든 좋아요 버튼 상태 업데이트
 * @param {number} productId - 상품 ID
 * @param {boolean} isLiked - 좋아요 상태
 */
function updateAllLikeButtonsForProduct(productId, isLiked) {
    // 모든 상품 카드의 좋아요 버튼 찾기
    const allLikeButtons = document.querySelectorAll(`.like-button[data-product-id="${productId}"]`);
    
    allLikeButtons.forEach(button => {
        const heartIcon = button.querySelector('.material-icons');
        if (heartIcon) {
            if (isLiked) {
                heartIcon.classList.remove('text-gray-400');
                heartIcon.classList.add('text-red-500');
            } else {
                heartIcon.classList.remove('text-red-500');
                heartIcon.classList.add('text-gray-400');
            }
        }
    });
    
    // 모달의 좋아요 버튼도 업데이트
    const modalLikeButton = document.getElementById('detail-like-button');
    const detailProductId = document.getElementById('detail-product-id');
    
    if (modalLikeButton && detailProductId && parseInt(detailProductId.value) === productId) {
        const modalHeartIcon = modalLikeButton.querySelector('.material-icons');
        if (modalHeartIcon) {
            if (isLiked) {
                modalHeartIcon.classList.remove('text-gray-400');
                modalHeartIcon.classList.add('text-red-500');
            } else {
                modalHeartIcon.classList.remove('text-red-500');
                modalHeartIcon.classList.add('text-gray-400');
            }
        }
    }
}

/**
 * CSRF 토큰 가져오기
 * @returns {string} CSRF 토큰
 */
function getCsrfToken() {
    const csrfCookie = document.cookie
        .split(';')
        .map(cookie => cookie.trim())
        .find(cookie => cookie.startsWith('csrftoken='));
        
    return csrfCookie ? csrfCookie.split('=')[1] : '';
}

/**
 * 상품 상세 정보 모달 표시 함수
 * @param {number} productId - 상품 ID
 * @param {Event} event - 클릭 이벤트 (옵션)
 */
function showProductDetail(productId, event) {
    if (event) {
        event.stopPropagation();
    }
    
    console.log("showProductDetail 호출됨:", productId);
    
    // productId가 문자열로 전달된 경우 숫자로 변환
    productId = parseInt(productId);
    
    // 캐시된 상품 정보가 있으면 좋아요 상태를 업데이트하고 표시
    if (productDetailsCache[productId]) {
        // 좋아요 상태를 캐시에서 업데이트
        if (typeof likedProductsCache[productId] !== 'undefined') {
            productDetailsCache[productId].is_liked = likedProductsCache[productId];
        }
        displayProductDetail(productDetailsCache[productId]);
        return;
    }
    
    // 캐시된 정보가 없으면 API로 상품 정보 가져오기
    fetch(`/Product/details/${productId}/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('상품 정보를 가져오는데 실패했습니다.');
            }
            return response.json();
        })
        .then(product => {
            // 좋아요 상태가 캐시에 있으면 API 응답보다 캐시 우선
            if (typeof likedProductsCache[productId] !== 'undefined') {
                product.is_liked = likedProductsCache[productId];
            }
            
            // 상품 정보 캐싱
            productDetailsCache[productId] = product;
            displayProductDetail(product);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('상품 정보를 불러오는 중 오류가 발생했습니다.');
        });
}

/**
 * 상품 상세 정보 모달에 정보 표시 함수
 * @param {Object} product - 상품 정보 객체
 */
function displayProductDetail(product) {
    const modal = document.getElementById('product-detail-modal');
    const modalContent = modal.querySelector('.modal-content');
    
    // 상품 ID 저장
    const detailProductId = document.getElementById('detail-product-id');
    if (detailProductId) {
        detailProductId.value = product.id;
    }
    
    // 기본 정보 설정
    const titleElem = document.getElementById('detail-title');
    if (titleElem) {
        titleElem.textContent = product.title || '제목 없음';
    }
    
    const brandElem = document.getElementById('detail-brand');
    if (brandElem) {
        brandElem.textContent = product.brand || '';
    }
    
    // 평점 정보 설정
    const ratingValueElem = document.getElementById('detail-rating-value');
    if (ratingValueElem) {
        ratingValueElem.textContent = product.average_rating ? product.average_rating.toFixed(1) : 'N/A';
    }
    
    const reviewsElem = document.getElementById('detail-reviews');
    if (reviewsElem) {
        reviewsElem.textContent = product.total_reviews ? `(${product.total_reviews} 리뷰)` : '(0 리뷰)';
    }
    
    // 별점 시각화
    const starsContainer = document.getElementById('detail-stars');
    if (starsContainer) {
        const stars = starsContainer.querySelectorAll('.material-icons');
        const rating = Math.round(product.average_rating || 0);
        
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.remove('text-yellow-200');
                star.classList.add('text-yellow-500');
            } else {
                star.classList.remove('text-yellow-500');
                star.classList.add('text-yellow-200');
            }
        });
    }
    
    // 좋아요 버튼 설정
    const likeButton = document.getElementById('detail-like-button');
    if (likeButton) {
        const heartIcon = likeButton.querySelector('.material-icons');
        
        // 좋아요 상태 확인
        const isLiked = product.is_liked || likedProductsCache[product.id] || false;
        
        // 아이콘 업데이트
        if (heartIcon) {
            if (isLiked) {
                heartIcon.classList.remove('text-gray-400');
                heartIcon.classList.add('text-red-500');
            } else {
                heartIcon.classList.remove('text-red-500');
                heartIcon.classList.add('text-gray-400');
            }
            
            // 캐시 업데이트
            likedProductsCache[product.id] = isLiked;
        }
        
        // 좋아요 버튼 클릭 이벤트 설정
        likeButton.onclick = function(e) {
            toggleLike(e, String(product.id));
            e.stopPropagation();
        };
    }
    
    // 가격 정보 - 총 가격과 개당 가격 분리하여 표시
    const totalPriceElem = document.getElementById('detail-total-price');
    const unitPriceElem = document.getElementById('detail-unit-price');
    
    // 총 가격 표시
    if (totalPriceElem && product.total_price) {
        totalPriceElem.textContent = `$${Number(product.total_price).toFixed(2)}`;
        if (totalPriceElem.parentElement) {
            totalPriceElem.parentElement.classList.remove('hidden');
        }
    } else if (totalPriceElem) {
        totalPriceElem.textContent = '정보 없음';
        if (totalPriceElem.parentElement) {
            totalPriceElem.parentElement.classList.add('hidden');
        }
    }
    
    // 개당 가격 표시
    if (unitPriceElem && product.price_value) {
        unitPriceElem.textContent = `$${Number(product.price_value).toFixed(2)}/개`;
        if (unitPriceElem.parentElement) {
            unitPriceElem.parentElement.classList.remove('hidden');
        }
    } else if (unitPriceElem) {
        unitPriceElem.textContent = '정보 없음';
        if (unitPriceElem.parentElement) {
            unitPriceElem.parentElement.classList.add('hidden');
        }
    }
    
    // 제품 상세 정보
    const ingredientsElem = document.getElementById('detail-ingredients');
    if (ingredientsElem) {
        ingredientsElem.textContent = product.ingredients || '성분 정보 없음';
    }
    
    const directionsElem = document.getElementById('detail-directions');
    if (directionsElem) {
        directionsElem.textContent = product.directions || '복용법 정보 없음';
    }
    
    const safetyElem = document.getElementById('detail-safety');
    if (safetyElem) {
        safetyElem.textContent = product.safety_info || '안전 정보 없음';
    }
    
    const supplementTypeElem = document.getElementById('detail-supplement-type');
    if (supplementTypeElem) {
        supplementTypeElem.textContent = product.supplement_type || '';
    }
    
    // 제품 형태 및 수량
    const productFormElem = document.getElementById('detail-product-form');
    if (productFormElem) {
        productFormElem.textContent = product.product_form || '정보 없음';
    }
    
    const quantityElem = document.getElementById('detail-quantity');
    if (quantityElem) {
        quantityElem.textContent = product.quantity || '정보 없음';
    }
    
    // 이미지 설정
    const detailImage = document.getElementById('detail-image');
    if (detailImage) {
        if (product.image_link) {
            detailImage.src = product.image_link;
            detailImage.onerror = function() {
                this.src = '/static/image/Logo.png';
            };
        } else {
            detailImage.src = '/static/image/Logo.png';
        }
    }
    
    // 비건 여부 표시
    const veganBadge = document.getElementById('detail-vegan');
    if (veganBadge) {
        if (product.vegan && (product.vegan.toLowerCase() === 'yes' || product.vegan.toLowerCase() === '예')) {
            veganBadge.classList.remove('hidden');
        } else {
            veganBadge.classList.add('hidden');
        }
    }
    
    // 다이어트 타입 표시
    const dietTypeBadge = document.getElementById('detail-diet-type');
    if (dietTypeBadge) {
        if (product.diet_type) {
            dietTypeBadge.textContent = product.diet_type;
            dietTypeBadge.classList.remove('hidden');
        } else {
            dietTypeBadge.classList.add('hidden');
        }
    }
    
    // 구매 링크
    const urlElem = document.getElementById('detail-url');
    if (urlElem) {
        if (product.url) {
            urlElem.href = product.url;
            urlElem.classList.remove('hidden');
        } else {
            urlElem.classList.add('hidden');
        }
    }
    
    // 모달 표시 (애니메이션 적용)
    modal.classList.remove('hidden');
    
    // 애니메이션을 위해 약간의 지연 후 show 클래스 추가
    setTimeout(() => {
        modal.classList.add('show');
        modalContent.classList.add('show');
    }, 10);
    
    console.log("모달 표시됨");
    
    // 모달 외부 클릭 이벤트 처리
    modal.onclick = function(e) {
        if (e.target === modal) {
            closeProductDetail();
        }
    };
}

/**
 * 상품 상세 정보 모달 닫기 함수
 * @param {Event} event - 클릭 이벤트 (옵션)
 */
function closeProductDetail(event) {
    if (event) {
        event.stopPropagation();
    }
    
    console.log("closeProductDetail 호출됨");
    const modal = document.getElementById('product-detail-modal');
    const modalContent = modal ? modal.querySelector('.modal-content') : null;
    
    if (modal && modalContent) {
        // 애니메이션 효과를 위해 show 클래스 제거
        modal.classList.remove('show');
        modalContent.classList.remove('show');
        
        // 애니메이션이 완료된 후 hidden 클래스 추가
        setTimeout(() => {
            modal.classList.add('hidden');
            console.log("모달 닫힘");
        }, 300); // 애니메이션 시간과 동일하게 설정
    } else {
        console.error("모달 요소를 찾을 수 없습니다");
    }
}

/**
 * 모달 초기화 함수 - 페이지 로드 시 호출
 */
function initProductModal() {
    // 모달 외부 클릭 시 닫기
    document.addEventListener('click', function(e) {
        const modal = document.getElementById('product-detail-modal');
        const modalContent = document.querySelector('#product-detail-modal > div');
        
        // 모달이 표시 중이고, 클릭이 모달 내부가 아닌 경우에만 닫기
        if (modal && 
            !modal.classList.contains('hidden') && 
            modalContent && 
            !modalContent.contains(e.target) && 
            !e.target.closest('.product-card')) {
            closeProductDetail();
        }
    });
    
    console.log('Product modal initialized');
}

// 상품 카드를 클릭할 때 모달 표시하는 이벤트 리스너 추가 함수
function attachProductCardListeners() {
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach(card => {
        const productId = card.getAttribute('data-product-id');
        card.addEventListener('click', (e) => {
            e.stopPropagation(); // 이벤트 버블링 방지
            showProductDetail(productId, e);
        });
    });
}

// 캐러셀 이동 함수
function moveCarousel(direction) {
    const carouselInner = document.querySelector('.carousel-inner');
    if (!carouselInner) return;
    
    const productCards = carouselInner.querySelectorAll('.product-card');
    if (productCards.length === 0) return;
    
    const cardWidth = productCards[0].offsetWidth + 16; // 카드 너비 + 마진
    const visibleCards = Math.floor(carouselInner.offsetWidth / cardWidth);
    
    // 현재 위치 업데이트
    let currentCarouselPosition = parseInt(carouselInner.getAttribute('data-position') || '0');
    currentCarouselPosition += direction;
    
    // 범위 제한
    if (currentCarouselPosition < 0) currentCarouselPosition = 0;
    if (currentCarouselPosition > productCards.length - visibleCards) {
        currentCarouselPosition = productCards.length - visibleCards;
    }
    
    // 위치 저장 및 적용
    carouselInner.setAttribute('data-position', currentCarouselPosition);
    carouselInner.style.transform = `translateX(-${currentCarouselPosition * cardWidth}px)`;
}

// 상품 카드 캐러셀 생성 함수
function createProductCarousel(products, containerElement) {
    if (!products || products.length === 0 || !containerElement) return;
    
    // 캐러셀 컨테이너 생성
    const carouselContainer = document.createElement('div');
    carouselContainer.className = 'product-carousel mb-4';
    
    // 캐러셀 HTML 생성
    let carouselHTML = `
        <div class="carousel-container">
            <div class="carousel-inner" data-position="0">
    `;
    
    // 각 상품 카드 추가
    products.forEach(product => {
        // 가격 정보 처리
        let priceHTML = '';
        
        if (product.total_price) {
            priceHTML += `<span class="total-price">$${Number(product.total_price).toFixed(2)}</span>`;
        }
        
        // 비건 태그 처리
        const isVegan = product.vegan && (product.vegan.toLowerCase() === 'yes' || product.vegan.toLowerCase() === '예');
        const veganTag = isVegan ? 
            `<span class="px-2 py-1 rounded-full text-xs font-medium bg-yellow-200 text-yellow-800 inline-block">비건</span>` : '';
        
        // 영양제 타입 태그
        const supplementTypeTag = product.supplement_type ? 
            `<span class="px-2 py-1 rounded-full text-xs font-medium bg-yellow-200 text-yellow-800 inline-block mr-1">${product.supplement_type}</span>` : '';
        
        // 좋아요 상태 확인
        const isLiked = product.is_liked || likedProductsCache[product.id] || false;
        const heartClass = isLiked ? 'text-red-500' : 'text-gray-400';
        
        carouselHTML += `
            <div class="product-card" data-product-id="${product.id}">
                <div class="product-image">
                    ${product.image_link ? 
                        `<img src="${product.image_link}" alt="${product.title}" onerror="this.src='/static/image/Logo.png'">` : 
                        `<div class="no-image">이미지 없음</div>`
                    }
                    <button class="like-button" data-product-id="${product.id}" onclick="toggleLike(event, '${product.id}')">
                        <span class="material-icons ${heartClass}">favorite</span>
                    </button>
                </div>
                <div class="product-info">
                    <h3 class="product-title">${product.title}</h3>
                    <p class="product-brand">${product.brand || ''}</p>
                    <div class="product-price mb-1">${priceHTML}</div>
                    <div class="product-rating">
                        <span class="stars">
                            ${Array(5).fill().map((_, i) => 
                                `<span class="material-icons ${i < Math.round(product.average_rating || 0) ? 'text-yellow-500' : 'text-yellow-200'}">star</span>`
                            ).join('')}
                        </span>
                        <span class="rating-value">${product.average_rating ? product.average_rating.toFixed(1) : 'N/A'}</span>
                        <span class="review-count">(${product.total_reviews || 0})</span>
                    </div>
                    <div class="product-tags mt-2">
                        ${supplementTypeTag}
                        ${veganTag}
                    </div>
                </div>
            </div>
        `;
    });
    
    // 캐러셀 닫기 및 컨트롤 버튼 추가
    carouselHTML += `
            </div>
            <button class="carousel-control prev" onclick="moveCarousel(-1)">
                <span class="material-icons">chevron_left</span>
            </button>
            <button class="carousel-control next" onclick="moveCarousel(1)">
                <span class="material-icons">chevron_right</span>
            </button>
        </div>
    `;
    
    // HTML 설정 및 컨테이너에 추가
    carouselContainer.innerHTML = carouselHTML;
    containerElement.appendChild(carouselContainer);
    
    // 상품 카드에 클릭 이벤트 추가
    const productCards = carouselContainer.querySelectorAll('.product-card');
    productCards.forEach(card => {
        const productId = card.getAttribute('data-product-id');
        card.addEventListener('click', (e) => {
            // 좋아요 버튼 클릭은 이벤트 버블링 방지
            if (!e.target.closest('.like-button')) {
                e.stopPropagation(); // 이벤트 버블링 방지
                showProductDetail(productId, e);
            }
        });
    });
    
    return carouselContainer;
}

// 페이지 로드 시 모달 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 모달이 페이지에 포함되어 있는지 확인
    if (document.getElementById('product-detail-modal')) {
        initProductModal();
    }
}); 