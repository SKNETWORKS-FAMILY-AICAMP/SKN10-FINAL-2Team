document.querySelectorAll('.heart-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
        const likeItem = btn.closest('.like-item');
        const productId = likeItem.dataset.productId;
        const isLiked = btn.classList.contains('liked');
        const url = isLiked ? "{% url 'like_delete' %}" : "{% url 'like_add' %}";

        fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": "{{ csrf_token }}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: "product_id=" + encodeURIComponent(productId)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                if (isLiked) {
                    btn.classList.remove('liked');
                    btn.innerHTML = "&#9825;"; // 빈 하트
                } else {
                    btn.classList.add('liked');
                    btn.innerHTML = "&#10084;"; // 채운 하트
                }
            } else {
                alert("처리 실패: " + (data.error || "알 수 없는 오류"));
            }
        });
    });
});

document.querySelectorAll('.product-container').forEach(function(container) {
    container.addEventListener('click', function(e) {
        // 하트 버튼 클릭 시에는 모달 안 뜨게
        if (e.target.classList.contains('heart-btn')) return;

        const item = container.closest('.like-item');
        const title = item.querySelector('.body-font').innerText;
        const manufacturer = item.querySelector('.caption-font').innerText;
        const price = item.querySelector('.body-font[style*="color: #DCA628;"]')?.innerText || '';
        const rating = item.querySelector('.caption-font span')?.parentNode.innerText || '';
        const imgSrc = container.querySelector('img').src;

        // 모달 내용 구성
        document.getElementById('modal-body').innerHTML = `
            <img src="${imgSrc}" alt="상품 이미지" style="width:160px;height:160px;object-fit:contain;display:block;margin:0 auto 16px auto;">
            <div style="font-size:20px;font-weight:700;margin-bottom:8px;">${title}</div>
            <div style="color:#7D97A1;margin-bottom:8px;">${manufacturer}</div>
            <div style="color:#DCA628;margin-bottom:8px;">${price}</div>
            <div style="color:#7D97A1;">${rating}</div>
        `;
        document.getElementById('product-modal').style.display = 'flex';
    });
});
document.querySelector('.modal-close').onclick = function() {
    document.getElementById('product-modal').style.display = 'none';
};
document.getElementById('product-modal').onclick = function(e) {
    if (e.target === this) this.style.display = 'none';
};
