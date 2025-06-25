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
    node_messages = state.get("node_messages", [])

    # 가장 최근 사용자 메시지 추출
    messages = state.get("messages", [])
    if not messages:
        return {"conversation_type": "general"}
    
    latest_message = messages[-1]
    if latest_message.type != "human":
        return {"conversation_type": "general"}
    
    user_query = latest_message.content
    
    # 시스템 프롬프트 정의
    system_prompt = """당신은 사용자의 메시지를 분석하여 대화 유형을 분류하는 전문가입니다. 각 메시지를 다음 기준에 따라 정확하게 분류해주세요.

[대화 유형 분류]
1. "general" (일반 대화)
   - 일상적인 대화, 인사, 감사 표현
   - 날씨, 기분 등 일반적인 주제
   - 예시: "안녕하세요", "감사합니다", "오늘 날씨가 좋네요"

2. "nutrient" (영양소 관련)
   - 특정 영양소의 효능, 기능에 대한 질문
   - 영양소의 건강상 이점에 대한 문의
   - 예시: "비타민 C의 효능이 궁금해요", "칼슘은 어떤 역할을 하나요?"

3. "supplement" (영양제 관련)
   - 특정 영양제 제품 추천 요청
   - 영양제의 효과나 사용법 문의
   - 예시: "비타민 C 영양제 추천해주세요", "눈 건강에 좋은 영양제가 있을까요?"

[응답 형식]
다음 JSON 형식으로 응답해주세요:
{
  "conversation_type": "general" | "nutrient" | "supplement",
  "confidence": 0.0-1.0,
  "explanation": "분류 근거에 대한 간단한 설명"
}

주의사항:
- 각 분류에 대한 확신도(confidence)는 0.0에서 1.0 사이의 값으로 표현
- 불확실한 경우 낮은 confidence 값을 부여
- explanation 필드에는 분류 결정의 주요 근거를 간단히 설명"""

    # LLM에 요청하여 대화 유형 분류
    result = get_llm_json_response(
        system_prompt=system_prompt,
        user_prompt=user_query
    )
    
    conversation_type = result.get("conversation_type", "general")

    if conversation_type == "general":
        node_messages.append("analyze_input 노드: '사용자의 입력이 영양소, 영양제 관련이 아닌 일반 대화 목적으로 판단되었습니다.'")
    elif conversation_type == "nutrient":
        node_messages.append("analyze_input 노드: '사용자의 입력이 영양소 정보 검색 목적으로 판단되었습니다.'")
    elif conversation_type == "supplement":
        node_messages.append("analyze_input 노드: '사용자의 입력이 영양제 상품 검색 목적으로 판단되었습니다.'")
    else:
        node_messages.append("analyze_input 노드: '사용자의 입력 목적을 판별할 수 없었습니다.'")

    print("질문 분석이 끝났어요!", conversation_type)
    # 변경된 상태 필드만 반환
    return {
        "conversation_type": conversation_type,
        "node_messages": node_messages
    } 