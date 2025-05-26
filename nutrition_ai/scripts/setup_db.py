import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.db.session import engine
from app.models.base import Base
from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

def init_db():
    # 데이터베이스 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    # 관리자 계정 생성
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "sknfinalteam2@gmail.com").first()
        if not admin:
            admin = User(
                email="sknfinalteam2@gmail.com",
                hashed_password=get_password_hash("ghkdlxld2@"),
                name="Admin",
                is_guest=False
            )
            db.add(admin)
            db.commit()
            print("관리자 계정이 생성되었습니다.")
    finally:
        db.close()

if __name__ == "__main__":
    print("데이터베이스 초기화를 시작합니다...")
    init_db()
    print("데이터베이스 초기화가 완료되었습니다.") 