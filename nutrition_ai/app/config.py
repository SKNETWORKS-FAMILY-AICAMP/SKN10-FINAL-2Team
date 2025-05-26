from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # 데이터베이스 설정
    DATABASE_URL: str
    
    # JWT 설정
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # OpenAI 설정
    OPENAI_API_KEY: str
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 