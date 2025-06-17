from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage

from ..state import AgentState
from .base import get_llm_response

def handle_general_chat(state: AgentState) -> Dict[str, Any]:
    """
    일반 대화를 처리하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    print("일반 대화 처리를 시작했어요!")

    # 가장 최근 사용자 메시지 추출
    messages = state.get("messages", [])
    if not messages:
        return {}
    
    # 대화 컨텍스트 구성 (최대 5개의 최근 메시지)
    conversation_context = []
    for msg in messages[-5:]:
        if msg.type == "human":
            conversation_context.append(f"사용자: {msg.content}")
        elif msg.type == "ai":
            conversation_context.append(f"챗봇: {msg.content}")
    
    conversation_history = "\n".join(conversation_context)
    print("대화 내용:\n", conversation_history)
    # 시스템 프롬프트 정의
    system_prompt = """당신은 영양제와 영양소에 관한 전문 지식을 갖춘 친절한 챗봇입니다.
사용자의 일반적인 질문에 명확하고 간결하게 답변해주세요.

답변 작성 지침:
1. 시간 순으로 나열된 대화 내용의 맥락을 파악하되, 가장 최근의 대화내용을 중점으로 답변을 작성하세요.
2. 친절하고 전문적인 톤을 유지하세요.
3. 간결하게 응답하되, 필요한 정보는 충분히 제공하세요.
4. 불확실한 정보는 제공하지 마세요.
5. 의학적 조언이 필요한 경우 전문가 상담을 권유하세요.
6. 사용자의 감정과 상황에 공감하는 태도를 보여주세요.
7. 답변 마지막에 영양소에 관련한 질문에 대한 답변과 영양제 상품 검색을 요청할 수 있음을 알려주세요.

응답 형식:
- 인사에는 간단하게 인사로 응답
- 감사 표현에는 정중하게 응답
- 도움 요청에는 명확한 안내 제공
- 불만 사항에는 공감하고 해결책 제시
- 영양소 정보 검색, 영양제 상품 검색이 가능함을 설명"""

    # 사용자 프롬프트 구성
    user_prompt = f"""대화 기록(시간 순):
{conversation_history}

사용자의 최근 메시지에 응답해주세요."""

    # LLM에 요청하여 응답 생성
    response = get_llm_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    print("일반 대화 처리를 끝냈어요!")

    # 변경된 상태 필드만 반환
    return {
        "response": response
    } 