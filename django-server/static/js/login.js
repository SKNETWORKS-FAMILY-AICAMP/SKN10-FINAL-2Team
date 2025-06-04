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
        loginForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            // 간단한 로그인 시뮬레이션
            if (email === 'test@example.com' && password === 'password123') {
                showSmallInfoPopup('로그인 성공!'); // 성공 시 작은 팝업으로 변경
            } else {
                showLoginFailedPopup('로그인 실패', '이메일 또는 비밀번호가 올바르지 않습니다.');
            }
        });
    }
    
    // 회원가입 모달 - 가입 버튼 (간단 시뮬레이션)
    if(signupSubmitButton) {
        signupSubmitButton.addEventListener('click', function() {
            const nameInput = document.getElementById('signupName');
            const emailInput = document.getElementById('signupEmail');
            const passwordInput = document.getElementById('signupPassword');
            const birthdateInput = document.getElementById('signupBirthdate');

            // 간단한 유효성 검사 예시 (실제로는 더 상세해야 함)
            if (nameInput.value && emailInput.value && passwordInput.value) {
                 closeModal(signupModal);
                 showSmallInfoPopup(`${nameInput.value}님, 회원가입 요청이<br>처리되었습니다 (시뮬레이션).`);
                 // 성공 후 필드 초기화 (선택적)
                 nameInput.value = '';
                 emailInput.value = '';
                 passwordInput.value = '';
                 birthdateInput.value = '';
            } else {
                 alert("이름, 이메일, 비밀번호는 필수 입력 항목입니다.");
            }
        });
    }

    // "이메일 찾기" 버튼
    if (findEmailButton) {
        findEmailButton.addEventListener('click', function() {
            const nameInput = document.getElementById('findEmailName');
            const identifierInput = document.getElementById('findEmailIdentifier');

            // 시뮬레이션: 실제로는 서버와 통신
            if (nameInput.value === 'test' && identifierInput.value === '12345678') {
                showSmallInfoPopup(`고객님의 이메일 주소는<br><b>test_kim@example.com</b> 입니다.`);
            } else {
                showSmallInfoPopup('입력하신 정보와 일치하는<br>이메일을 찾을 수 없습니다.<br>다시 입력해주세요.');
            }
            // 조회 후 필드 초기화 (선택적)
            // nameInput.value = '';
            // identifierInput.value = '';
        });
    }

    // "비밀번호 찾기" 버튼
    if (findPasswordButton) {
        findPasswordButton.addEventListener('click', function() {
            const nameInput = document.getElementById('findPassName');
            const emailInput = document.getElementById('findPassEmail');
            const birthdateInput = document.getElementById('findPassBirthdate');

            // 시뮬레이션: 실제로는 서버와 통신
            if (nameInput.value === 'test' && emailInput.value === 'test_lee@example.com' && birthdateInput.value === '19950101') {
                closeModal(findCredentialsModal);
                openModal(resetPasswordModal);
                // 성공 후 필드 초기화 (선택적)
                nameInput.value = '';
                emailInput.value = '';
                birthdateInput.value = '';
            } else {
                showSmallInfoPopup('입력하신 정보와 일치하는 사용자를<br>찾을 수 없습니다.<br>다시 확인해주세요.');
            }
        });
    }

    // "비밀번호 재설정" 모달 - "저장" 버튼
    if (saveNewPasswordButton) {
        saveNewPasswordButton.addEventListener('click', function() {
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

            // 성공 시 (시뮬레이션)
            closeModal(resetPasswordModal);
            showSmallInfoPopup('비밀번호를 성공적으로<br>변경했습니다.');
            
            // 성공 후 입력 필드 초기화
            newPasswordInput.value = '';
            confirmNewPasswordInput.value = '';
        });
    }
});