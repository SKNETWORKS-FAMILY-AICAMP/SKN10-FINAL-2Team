from typing import Dict, Any, Optional, TypeVar, Generic, Callable
from django.conf import settings
from openai import OpenAI
import os
from dotenv import load_dotenv

from ..state import AgentState

# 환경변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def get_llm_response(
    system_prompt: str, 
    user_prompt: str, 
    model: str = "gpt-4o-mini", 
    temperature: float = 0.1, 
    response_format: Optional[Dict[str, str]] = None
) -> str:
    """
    LLM에 요청을 보내고 응답을 받는 유틸리티 함수
    
    Args:
        system_prompt: 시스템 프롬프트
        user_prompt: 사용자 프롬프트
        model: 사용할 모델
        temperature: 온도 설정
        response_format: 응답 형식 (예: {"type": "json_object"})
        
    Returns:
        LLM의 응답 텍스트
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    if response_format:
        kwargs["response_format"] = response_format
    
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

def get_llm_json_response(
    system_prompt: str, 
    user_prompt: str, 
    model: str = "gpt-4o-mini", 
    temperature: float = 0.1,
    response_format_json: bool = True
) -> Dict[str, Any]:
    """
    JSON 형식의 응답을 반환하는 LLM 요청
    
    Args:
        system_prompt: 시스템 프롬프트
        user_prompt: 사용자 프롬프트
        model: 사용할 모델
        temperature: 온도 설정
        
    Returns:
        LLM의 응답을 파싱한 딕셔너리
    """
    import json
    
    response_text = get_llm_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"} if response_format_json else None
    )

    if response_format_json:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            print(f"JSON 파싱 오류: {response_text}")
            return {}
    else:
        return response_text