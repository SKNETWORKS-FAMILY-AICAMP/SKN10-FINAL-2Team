function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function logoutUser() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    // 로그인 페이지로 리다이렉트 (YOUR_LOGIN_URL을 실제 로그인 페이지 URL로 변경)
    window.location.href = '/login/'; 
}

/**
 * 사용자 인증 상태를 확인하고, 필요시 토큰을 재발급합니다.
 * @returns {boolean} 사용자가 현재 인증된 상태인지 여부 (Access Token 유효 또는 성공적으로 재발급됨)
 */
async function checkUserAuthentication() {
    let accessToken = localStorage.getItem('accessToken');
    const refreshToken = localStorage.getItem('refreshToken');

    // 1. Access Token이 없는 경우: 로그인 필요
    if (!accessToken) {
        console.log("Access Token not found. User needs to log in.");
        // showSmallInfoPopup('로그인이 필요합니다.'); // 필요시 메시지 표시
        // logoutUser(); // 토큰이 없으므로 강제 로그아웃 (사실상 로그인 페이지로 유도)
        return false;
    }

    // 2. Access Token 유효성 검사
    try {
        // Access Token이 유효한지 백엔드에 확인 (선택 사항이지만 가장 정확)
        // Simple JWT의 token/verify 엔드포인트를 사용합니다.
        const verifyResponse = await fetch('/api/token/verify/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`, // 현재 Access Token 사용
                'X-CSRFToken': getCookie('csrftoken') // CSRF 토큰도 함께 전송
            },
            body: JSON.stringify({ token: accessToken }) // Access Token을 body에 포함
        });

        if (verifyResponse.ok) {
            console.log("Access Token is valid.");
            return true; // Access Token 유효, 인증 완료
        } else if (verifyResponse.status === 401) {
            // Access Token이 만료되었거나 유효하지 않음 -> Refresh Token 시도
            console.warn("Access Token expired or invalid. Attempting to refresh.");
            
            // 3. Refresh Token으로 Access Token 재발급 시도
            if (!refreshToken) {
                console.error("Refresh Token not found. Cannot refresh Access Token.");
                logoutUser();
                return false;
            }

            const refreshResponse = await fetch('/api/token/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ refresh: refreshToken })
            });

            if (refreshResponse.ok) {
                const data = await refreshResponse.json();
                const newAccessToken = data.access;
                localStorage.setItem('accessToken', newAccessToken); // 새 Access Token 저장
                console.log("Access Token refreshed successfully.");
                return true; // 새 Access Token으로 인증 완료
            } else if (refreshResponse.status === 401) {
                console.error("Refresh Token expired or invalid. User needs to log in again.");
                logoutUser(); // Refresh Token마저 만료, 강제 로그아웃
                return false;
            } else {
                console.error("Failed to refresh token:", await refreshResponse.json());
                logoutUser();
                return false;
            }
        } else {
            console.error("Token verification failed with status:", verifyResponse.status, await verifyResponse.json());
            logoutUser(); // 그 외 알 수 없는 오류는 로그아웃 처리
            return false;
        }

    } catch (error) {
        console.error("Network or server error during token verification/refresh:", error);
        logoutUser(); // 네트워크 오류도 일단 로그아웃으로 처리 (보안상)
        return false;
    }
}

// const isAuthenticated = await checkUserAuthentication(); api 호출 전에 인증 했는지 확인 하는 코드 true 이면 인증, false면 거부