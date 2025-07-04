from typing import Dict, List, TypedDict, Any, Optional, Sequence, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# 새로 덮어씌우기 위한 리듀서 함수 정의
def overwrite_reducer(left: Any, right: Any) -> Any:
    """새로운 값을 기존 값에 덮어씌우는 리듀서."""
    return right # 단순히 새 값을 반환합니다.

# 새로 정의한 리듀서
def merge_dict(left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if right is None:
        return left or {}
    if left is None:
        return right or {}
    merged = left.copy()
    merged.update(right)
    return merged

class AgentState(TypedDict):
    """
    에이전트 시스템의 상태를 정의하는 TypedDict 클래스.
    LangGraph 워크플로우에서 상태 관리에 사용됩니다.
    """
    # 사용자 id
    user_id: Annotated[Optional[int], overwrite_reducer]

    # 메시지 기록
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 각각의 노드에서 수행한 작업을 저장
    node_messages: Annotated[Optional[List[Any]], overwrite_reducer]

    # 각각의 노드에서 수행한 작업을 요약
    node_messages_summary: Annotated[Optional[str], overwrite_reducer]
    
    # 사용자 건강 정보
    user_health_info: Annotated[Optional[Dict[str, Any]], merge_dict]
    
    # 대화 타입 (general, nutrient, supplement)
    conversation_type: Annotated[Optional[str], overwrite_reducer]

    # 개인화 추천여부 (True or False)
    is_personalized: Annotated[bool, overwrite_reducer]
    
    # AI 최종 답변
    response: Annotated[Optional[str], overwrite_reducer]

    # 영양제 검색을 위한 정보가 충분한지 여부
    is_enough_sup_info: Annotated[bool, overwrite_reducer]
    
    # 추출된 정보
    extracted_info: Annotated[Optional[Dict[str, Any]], merge_dict]
    
    # 개인화 분석 정보
    personalized_info: Annotated[Optional[Dict[str, Any]], overwrite_reducer]
    
    # KAG 쿼리 및 결과
    kag_query: Annotated[Optional[str], overwrite_reducer]
    kag_results: Annotated[Optional[List[Any]], overwrite_reducer]
    
    # 리랭킹 결과
    rerank_results: Annotated[Optional[List[Any]], overwrite_reducer]
    
    # 최종 결과
    final_results: Annotated[Optional[List[Any]], overwrite_reducer]
    
    # 추천된 상품 ID 목록
    product_ids: Annotated[Optional[List[Dict[str, Any]]], overwrite_reducer]

    # 영양소 검색을 위한 정보가 충분한지 여부
    is_enough_nut_info: Annotated[bool, overwrite_reducer]

    # 영양소 질문 시 어떤 영양소를 질문하는지
    nutrients: Annotated[Optional[List[str]], overwrite_reducer]
    
    # 영양소 질문 시 해당 영양소에 대한 지식을 저장하는 state
    nutrient_knowledge: Annotated[Optional[Dict[str, Any]], overwrite_reducer]
    
    # Human-in-the-loop 관련 필드
    followup_question: Annotated[Optional[str], overwrite_reducer]