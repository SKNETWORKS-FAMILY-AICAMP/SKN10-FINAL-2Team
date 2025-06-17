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
2. "nutrient": 영양소에 관한 질문 (효능, 상호작용, 섭취 방법, 부작용 등)
3. "supplement": 영양제 제품에 관한 질문 (추천 요청, 비교, 복용 방법, 가격 등)

분석 시 고려할 키워드:
- 영양소 관련: 비타민, 미네랄, 오메가3, 효능, 부작용, 상호작용, 섭취방법 등
- 영양제 관련: 제품, 브랜드, 추천, 비교, 가격, 복용법, 구매 등

JSON 형식으로 다음 정보를 반환해주세요:
{
  "conversation_type": "general" | "nutrient" | "supplement",
  "confidence": 0.0-1.0 (분류에 대한 확신도),
  "reasoning": "분류 이유에 대한 간략한 설명"
}"""

    # LLM에 요청하여 대화 유형 분류
    result = get_llm_json_response(
        system_prompt=system_prompt,
        user_prompt=user_query
    )
    
    conversation_type = result.get("conversation_type", "general")
    
    # 변경된 상태 필드만 반환
    return {"conversation_type": conversation_type} 