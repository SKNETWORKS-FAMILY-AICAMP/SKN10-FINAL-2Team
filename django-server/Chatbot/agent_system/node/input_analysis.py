from typing import Dict, Any
from langchain_core.messages import BaseMessage
import json

from ..state import AgentState
from .base import get_llm_json_response

def analyze_input(state: AgentState) -> Dict[str, Any]:
    """
    사용자 입력을 분석하여 대화 유형을 결정하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """

    print("질문 분석을 시작했어요!")

    # 가장 최근 사용자 메시지 추출
    messages = state.get("messages", [])
    if not messages:
        return {"conversation_type": "general"}
    
    latest_message = messages[-1]
    if latest_message.type != "human":
        return {"conversation_type": "general"}
    
    user_query = latest_message.content
    
    # 시스템 프롬프트 정의
    system_prompt = """당신은 사용자 메시지를 분석하여 대화 유형을 분류하는 전문가입니다.

다음 세 가지 대화 유형 중 하나로 분류해주세요:
1. "general": 일반적인 대화, 인사, 감사, 도움 요청 등
  - 예시: 안녕하세요. 감사합니다.
  - 예시: 오늘 날씨가 좋네요.
2. "nutrient": 영양소에 관한 질문
  - 예시: 비타민 C는 우리 몸에 어떤 효능이 있나요?
  - 예시: 피로회복에 좋은 성분을 알려주세요.
3. "supplement": 영양제 제품 검색 관한 질문
  - 예시: 피로 회복에 좋은 영양제 제품을 추천해주실 수 있나요?
  - 예시: 눈 건강에 도움이 되는 영양제를 추천해주세요.
  - 예시: 비타민 C 영양제를 추천해주세요.

JSON 형식으로 다음 정보를 반환해주세요:
{
  "conversation_type": "general" | "nutrient" | "supplement",
  "confidence": 0.0-1.0 (분류에 대한 확신도),
}"""

    # LLM에 요청하여 대화 유형 분류
    result = get_llm_json_response(
        system_prompt=system_prompt,
        user_prompt=user_query
    )
    
    conversation_type = result.get("conversation_type", "general")
    print("질문 분석이 끝났어요!", conversation_type)
    # 변경된 상태 필드만 반환
    return {"conversation_type": conversation_type} 