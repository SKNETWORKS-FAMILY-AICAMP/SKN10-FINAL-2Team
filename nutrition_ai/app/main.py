from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import user, supplement, auth
from app.core.exceptions import NutritionAIException
from app.utils.logger import app_logger
import time

app = FastAPI(
    title="영양제 AI 추천 서비스",
    description="사용자 맞춤형 영양제 추천 AI 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(supplement.router)

# 예외 처리
@app.exception_handler(NutritionAIException)
async def nutrition_ai_exception_handler(request: Request, exc: NutritionAIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    app_logger.info(
        f"Method: {request.method} Path: {request.url.path} "
        f"Status: {response.status_code} Duration: {process_time:.2f}s"
    )
    
    return response

@app.get("/")
async def root():
    return {"message": "영양제 AI 추천 서비스에 오신 것을 환영합니다!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 