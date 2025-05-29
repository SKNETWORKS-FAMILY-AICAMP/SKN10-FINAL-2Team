# 영양제 AI 추천 서비스

이 프로젝트는 사용자의 건강 상태와 요구사항을 기반으로 개인화된 영양제 추천을 제공하는 AI 기반 서비스입니다.

## 주요 기능

- 사용자 건강 정보 기반 영양제 추천
- LLM 기반 상담 서비스
- 성분 간 상호작용 검사
- 회원/비회원 서비스 지원

## 설치 방법

1. 저장소 클론
```bash
git clone [repository-url]
cd nutrition_ai
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
- `.env.example` 파일을 `.env`로 복사하고 필요한 값들을 설정

5. 데이터베이스 마이그레이션
```bash
alembic upgrade head
```

6. 서버 실행
```bash
uvicorn app.main:app --reload
```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 테스트

```bash
pytest
```

## 프로젝트 구조

```
nutrition_ai/
├── app/                    # 메인 애플리케이션 코드
├── tests/                  # 테스트 코드
├── alembic/               # 데이터베이스 마이그레이션
├── requirements.txt       # 프로젝트 의존성
└── README.md             # 프로젝트 문서
```

## 라이선스

MIT License 