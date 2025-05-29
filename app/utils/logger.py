import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(name: str, log_file: str = "app.log"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 콘솔 출력 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 출력 핸들러
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path / log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 애플리케이션 로거
app_logger = setup_logger("app")
# API 로거
api_logger = setup_logger("api", "api.log")
# LLM 로거
llm_logger = setup_logger("llm", "llm.log") 