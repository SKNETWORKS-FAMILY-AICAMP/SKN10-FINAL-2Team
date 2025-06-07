
let globalUidb64 = null;
let globalToken = null;


document.addEventListener('DOMContentLoaded', function () {
// 기본 요소
const loginForm = document.getElementById('loginForm');
const signupLink = document.getElementById('signupLink');
const findCredentialsLink = document.getElementById('findCredentialsLink');

// 모달 요소
const signupModal = document.getElementById('signupModal');
const findCredentialsModal = document.getElementById('findCredentialsModal');
const resetPasswordModal = document.getElementById('resetPasswordModal');

// 팝업 요소
const loginFailedPopup = document.getElementById('loginFailedPopup');
const smallInfoPopup = document.getElementById('smallInfoPopup');

// 닫기 버튼 (모든 모달/팝업의 X 버튼)
const closeButtons = document.querySelectorAll('.close-button');

// 팝업 내 확인/닫기 버튼 (data-modal 속성으로 제어)
const popupConfirmButtons = document.querySelectorAll('.btn-popup-confirm');

// 이메일/비번찾기 모달 내 버튼
const findEmailButton = document.getElementById('findEmailButton');
const findPasswordButton = document.getElementById('findPasswordButton');

// 비밀번호 재설정 모달 내 버튼
const saveNewPasswordButton = document.getElementById('saveNewPasswordButton');

// 회원가입 버튼
const signupSubmitButton = document.getElementById('signupSubmitButton');

// --- 유틸리티 함수 ---
function openModal(modal) {
    if (modal) modal.style.display = 'flex';
}

function closeModal(modal) {
    if (modal) modal.style.display = 'none';
}

function showSmallInfoPopup(message) {
    // innerHTML 사용 시 주의: 신뢰할 수 없는 소스에서 온 HTML을 직접 삽입하면 XSS 위험이 있습니다.
    // 이 예제에서는 개발자가 제어하는 문자열이므로 사용하지만, 사용자 입력을 직접 넣을 때는 textContent 등을 고려하세요.
    document.getElementById('smallInfoPopupMessage').innerHTML = message;
    openModal(smallInfoPopup);
}

function showLoginFailedPopup(title, message) {
    document.getElementById('loginFailedPopupTitle').textContent = title;
    document.getElementById('loginFailedPopupMessage').textContent = message;
    openModal(loginFailedPopup);
}
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
// --- 이벤트 리스너 ---

// 회원가입 링크
if (signupLink) {
    signupLink.addEventListener('click', function (e) {
        e.preventDefault();
        openModal(signupModal);
    });
}

// 이메일/비밀번호 찾기 링크
if (findCredentialsLink) {
    findCredentialsLink.addEventListener('click', function (e) {
        e.preventDefault();
        openModal(findCredentialsModal);
    });
}

// 모든 X 닫기 버튼
closeButtons.forEach(button => {
    button.addEventListener('click', function () {
        const modalToClose = document.getElementById(this.dataset.modal);
        if (modalToClose) {
            closeModal(modalToClose);
        }
    });
});

// 모든 팝업 내 확인/닫기 버튼
popupConfirmButtons.forEach(button => {
    button.addEventListener('click', function() {
        const modalToClose = document.getElementById(this.dataset.modal);
        if (modalToClose) {
            closeModal(modalToClose);
        }
    });
});

// 모달 외부 클릭 시 닫기
window.addEventListener('click', function (event) {
    if (event.target.classList.contains('modal')) {
        closeModal(event.target);
    }
});

// 로그인 폼 제출
if (loginForm) {
    loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        if (!email || !password) {
            showLoginFailedPopup('로그인 오류', '이메일과 비밀번호를 입력해주세요.');
            return;
        }

        const loginData = {
            email: email,
            password: password
        };

        try {
            const response = await fetch('/login/login/', { // Your new login API endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') // Include CSRF token for POST requests
                },
                body: JSON.stringify(loginData)
            });

            const result = await response.json(); // Parse response JSON

            if (response.ok) { // Check if status code is 2xx (success)
                showSmallInfoPopup(result.message);
                console.log("Login Success! Tokens:", result.access, result.refresh);
                // Store tokens (e.g., in localStorage or sessionStorage)
                localStorage.setItem('accessToken', result.access);
                localStorage.setItem('refreshToken', result.refresh);
                // Redirect to main page
                window.location.href = '/main/'; // Change to your actual main page URL
            } else {
                // Handle different error messages from the backend
                let errorMessage = "알 수 없는 로그인 오류가 발생했습니다.";
                if (result && result.detail) {
                    errorMessage = result.detail;
                } else if (result && result.message) {
                    errorMessage = result.message;
                } else if (result) {
                    errorMessage = JSON.stringify(result); // Fallback for unexpected error structures
                }
                showLoginFailedPopup('로그인 실패', errorMessage);
                console.error('Login failed:', result);
            }
        } catch (error) {
            console.error('Network or server error during login:', error);
            showLoginFailedPopup('네트워크 오류', '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
        }
    });
}

// 회원가입 모달 - 가입 버튼 
if (signupSubmitButton) {
    signupSubmitButton.addEventListener('click', async function(event) { // async 추가
        event.preventDefault(); // 기본 폼 제출 방지 (만약 버튼이 form 안에 있다면)

        const nameInput = document.getElementById('signupName');
        const emailInput = document.getElementById('signupEmail');
        const passwordInput = document.getElementById('signupPassword');
        const birthdateInput = document.getElementById('signupBirthdate');
        const genderIdInput = document.getElementById('signupGenderId');

        const username = nameInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const birth_date = birthdateInput.value; // YYYY-MM-DD 형식으로 가정
        const gender_id_raw = genderIdInput.value.trim();

        // 간단한 클라이언트 측 유효성 검사
        if (!username || !email || !password || !gender_id_raw || !birth_date) {
            alert("이름, 이메일, 비밀번호, 생년월일은 필수 입력 항목입니다.");
            return; // 유효성 검사 실패 시 함수 종료
        }
        const gender_id = parseInt(gender_id_raw, 10);
        if (isNaN(gender_id) || ![1, 2, 3, 4].includes(gender_id)) {
            showSmallInfoPopup('성별 번호는 1, 2, 3, 4 중 하나여야 합니다.');
            return;
        }
        // 서버로 보낼 데이터 객체
        const userData = {
            username: username,
            email: email,
            password: password,
            birth_date: birth_date, // birthdate가 비어있으면 null로 전송될 것임 (Serializer 설정에 따라)
            gender_id: gender_id
        };

        try {
            const response = await fetch('/login/signup/', { // Django API 엔드포인트
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') // CSRF 토큰 포함
                },
                body: JSON.stringify(userData)
            });

            const result = await response.json();

            if (response.ok) { // HTTP 상태 코드가 200번대인 경우
                closeModal(signupModal);
                showSmallInfoPopup(`${username}님, 회원가입이 성공적으로 완료되었습니다!`);
                // 성공 후 필드 초기화
                nameInput.value = '';
                emailInput.value = '';
                passwordInput.value = '';
                birthdateInput.value = '';
                genderIdInput.value = '';
            } else { // HTTP 상태 코드가 400, 500 등 오류인 경우
                let errorMessage = "회원가입 중 오류가 발생했습니다.";
                if (result && result.email) {
                    errorMessage = `오류: ${result.email.join(', ')}`; // 이메일 중복 등
                } else if (result && result.username) {
                    errorMessage = `오류: ${result.username.join(', ')}`;
                } else if (result && result.detail) {
                    errorMessage = `오류: ${result.detail}`;
                } else if (result && typeof result === 'object') {
                    errorMessage = "오류: " + JSON.stringify(result); // 기타 상세 오류
                }
                alert(errorMessage);
                console.error('Signup failed:', result);
            }
        } catch (error) {
            console.error('Fetch error:', error);
            alert("네트워크 오류 또는 서버에 연결할 수 없습니다.");
        }
    });
}


// "이메일 찾기" 버튼
if (findEmailButton) {
    findEmailButton.addEventListener('click', async function() {
        const name = document.getElementById('findEmailName').value.trim();
        const birth_date = document.getElementById('findEmailIdentifier').value;
        console.log('date',birth_date)
        if (!name || !birth_date) {
            showSmallInfoPopup('이름과 생년월일을 모두 입력해주세요.');
            return;
        }

        const findData = {
            name: name,
            birth_date: birth_date
        };
        try {
            const response = await fetch('/login/find-email/', { // 새로운 API 엔드포인트
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(findData)
            });

            const result = await response.json();

            if (response.ok) { // HTTP 상태 코드가 200번대인 경우 (성공)
                showSmallInfoPopup(`고객님의 이메일 주소는<br><b>${result.email}</b> 입니다.`);
            } else { // HTTP 상태 코드가 400, 500 등 오류인 경우
                let errorMessage = "이메일을 찾을 수 없습니다. 다시 시도해주세요.";
                if (result && result.non_field_errors) {
                    errorMessage = result.non_field_errors[0]; // Serializer.validate()에서 오는 오류
                } else if (result && result.detail) {
                    errorMessage = result.detail;
                } else if (result && result.name) {
                    errorMessage = `이름 오류: ${result.name.join(', ')}`;
                } else if (result && result.birth_date) {
                    errorMessage = `생년월일 오류: ${result.birth_date.join(', ')}`;
                }
                showSmallInfoPopup(`입력하신 정보와 일치하는<br>이메일을 찾을 수 없습니다.<br>${errorMessage}`);
                console.error('Find Email failed:', result);
            }
        } catch (error) {
            console.error('Network or server error during find email:', error);
            showSmallInfoPopup('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        }

    });
}

// "비밀번호 찾기" 버튼
if (findPasswordButton) {
    findPasswordButton.addEventListener('click', async function() {
        const nameInput = document.getElementById('findPassName');
        const emailInput = document.getElementById('findPassEmail');
        const birthdateInput = document.getElementById('findPassBirthdate');

        const name = nameInput.value.trim();
        const email = emailInput.value.trim();
        const birth_date = birthdateInput.value;

        if (!name || !email || !birth_date) {
            showSmallInfoPopup('이름, 이메일, 생년월일을 모두 입력해주세요.');
            return;
        }
        const resetRequestData = {
            name: name,
            email: email,
            birth_date: birth_date
        };
        try {
            const response = await fetch('/login/password-reset-request/', { // 비밀번호 재설정 요청 API
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(resetRequestData)
            });

            const result = await response.json();

            if (response.ok) {
                closeModal(findCredentialsModal); // 현재 모달 닫기
                showSmallInfoPopup(result.message); // "이메일 발송 완료" 메시지 표시
                
                // 성공 후 입력 필드 초기화 (선택적)
                nameInput.value = '';
                emailInput.value = '';
                birthdateInput.value = '';

            } else {
                let errorMessage = "비밀번호 재설정 요청 중 오류가 발생했습니다.";
                if (result && result.detail) {
                    errorMessage = result.detail;
                } else if (result && result.non_field_errors) {
                    errorMessage = result.non_field_errors[0];
                } else if (result && typeof result === 'object') {
                    const fieldErrors = Object.keys(result).map(key => `${key}: ${result[key].join(', ')}`).join('<br>');
                    errorMessage = fieldErrors || errorMessage;
                }
                showSmallInfoPopup(`오류: ${errorMessage}`);
                console.error('Password reset request failed:', result);
            }
        } catch (error) {
            console.error('Network or server error during password reset request:', error);
            showSmallInfoPopup('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        }
    });
}
const urlParams = new URLSearchParams(window.location.search);
const action = urlParams.get('action');
const uidb64 = urlParams.get('uidb64');
const token = urlParams.get('token');

// action이 'reset_password'이고 uidb64와 token이 URL에 있다면 비밀번호 재설정 모달을 띄웁니다.
if (action === 'reset_password' && uidb64 && token) {
    globalUidb64 = uidb64;
    globalToken = token;
    openModal(resetPasswordModal);

    // URL에서 파라미터 제거하여 깔끔하게 유지 (선택 사항)
    // 사용자가 새로고침했을 때 모달이 다시 뜨는 것을 방지
    window.history.replaceState({}, document.title, window.location.pathname);
}

// "비밀번호 재설정" 모달 - "저장" 버튼
if (saveNewPasswordButton) {
    saveNewPasswordButton.addEventListener('click', async function() {
        const newPasswordInput = document.getElementById('newPassword');
        const confirmNewPasswordInput = document.getElementById('confirmNewPassword');
        const newPassword = newPasswordInput.value;
        const confirmNewPassword = confirmNewPasswordInput.value;

        if (!newPassword || !confirmNewPassword) {
            showSmallInfoPopup('새 비밀번호와 확인 비밀번호를<br>모두 입력해주세요.');
            return;
        }
        if (newPassword !== confirmNewPassword) {
            showSmallInfoPopup('새 비밀번호와 확인 비밀번호가<br>일치하지 않습니다.');
            return;
        }
        // 비밀번호 유효성 검사 (예: 길이, 특수문자 등) 추가 가능
        if (newPassword.length < 8) {
            showSmallInfoPopup('비밀번호는 8자 이상이어야 합니다.');
            return;
        }

        // if (!uidb64 || !token) {
        //     // URL 정리를 했다면, uidb64와 token을 전역 변수나 localStorage에 저장하는 방법 고려.
        //     // 여기서는 URL 정리를 하지 않는다고 가정하거나, 에러 처리 메시지를 명확히 합니다.
        //     showSmallInfoPopup('비밀번호 재설정 정보가 누락되었습니다.<br>이메일 링크를 다시 확인해주세요.');
        //     closeModal(resetPasswordModal);
        //     return;
        // }
        const setNewPasswordData = {
            uidb64: globalUidb64,
            token: globalToken,
            new_password: newPassword,
            confirm_new_password: confirmNewPassword
        };
        // 성공 시 (시뮬레이션)
        try {
            const response = await fetch('/login/set-new-password/', { // 새 비밀번호 설정 API
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(setNewPasswordData)
            });

            const result = await response.json();

            if (response.ok) {
                closeModal(resetPasswordModal);
                showSmallInfoPopup('비밀번호를 성공적으로<br>변경했습니다.');
                
                // 성공 후 입력 필드 초기화
                newPasswordInput.value = '';
                confirmNewPasswordInput.value = '';
                globalUidb64 = null;
                globalToken = null;

                // 성공 후 로그인 페이지로 리다이렉트 (필요하다면)
                window.location.href = '/login/'; 
            } else {
                let errorMessage = "비밀번호 변경 중 오류가 발생했습니다.";
                if (result && result.detail) {
                    errorMessage = result.detail;
                } else if (result && result.new_password) {
                    errorMessage = `새 비밀번호: ${result.new_password.join(', ')}`;
                } else if (result && result.confirm_new_password) {
                    errorMessage = `확인 비밀번호: ${result.confirm_new_password.join(', ')}`;
                } else if (result && result.non_field_errors) {
                    errorMessage = result.non_field_errors.join(', ');
                } else if (result && typeof result === 'object') {
                    const fieldErrors = Object.keys(result).map(key => `${key}: ${result[key].join(', ')}`).join('<br>');
                    errorMessage = fieldErrors || errorMessage;
                }
                showSmallInfoPopup(`오류: ${errorMessage}`);
                console.error('Set new password failed:', result);
            }
        } catch (error) {
            console.error('Network or server error during password reset:', error);
            showSmallInfoPopup('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        }
        

    });
}
});