from typing import Dict, List, TypedDict, Any, Optional, Sequence, Annotated, Union
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from operator import add

class NutrientKnowledge(TypedDict):
    """영양소 관련 지식 데이터"""
    effects: List[Dict[str, Any]]  # 영양소 효능 정보
    interactions: List[Dict[str, Any]]  # 영양소 상호작용 정보
    combinations: List[Dict[str, Any]]  # 영양소 조합 정보

class NutrientSummary(TypedDict):
    """영양소 정보 요약"""
    primary_nutrients: List[str]  # 주요 영양소
    synergistic_nutrients: List[str]  # 상승작용 영양소
    antagonistic_nutrients: List[str]  # 상충작용 영양소
    recommended_forms: List[str]  # 권장 섭취 형태
    usage_guidelines: List[str]  # 섭취 가이드라인

class ExtractedInfo(TypedDict):
    """사용자 쿼리에서 추출된 정보"""
    nutrients: List[str]  # 직접 언급된 영양소
    flavors: List[str]  # 맛 데이터
    supplement_types: List[str]  # 영양제 종류
    quantities: List[str]  # 수량
    forms: List[str]  # 양식 (알약, 캡슐 등)
    order_ratings: Optional[bool]  # 별점 평점
    order_reviewcnt: Optional[bool]  # 리뷰 수
    prices: List[str]  # 가격
    origins: List[str]  # 원산지 국가
    is_vegan: Optional[bool]  # 비건 여부
    purpose_tag: List[str]  # 사용자의 목적 태그

class UserHealthInfo(TypedDict):
    """사용자 건강 정보"""
    age: Optional[int]
    gender: Optional[str]
    weight: Optional[float]
    height: Optional[float]
    allergies: List[str]
    medications: List[str]
    health_conditions: List[str]
    diet_restrictions: List[str]
    exercise_frequency: Optional[str]
    smoking: Optional[bool]
    alcohol_consumption: Optional[str]

class QueryResult(TypedDict):
    """쿼리 결과"""
    id: str
    name: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    price: Optional[float]
    quantity: Optional[str]
    is_vegan: Optional[bool]

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
    # 메시지 기록
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 사용자 입력
    user_query: Annotated[str, overwrite_reducer]
    
    # 사용자 건강 정보
    user_health_info: Annotated[Optional[Dict[str, Any]], merge_dict]
    
    # 대화 타입 (general, nutrient, supplement)
    conversation_type: Annotated[Optional[str], overwrite_reducer]
    
    # 추출된 정보
    extracted_info: Annotated[Optional[Dict[str, Any]], merge_dict]
    
    # KAG 쿼리 및 결과
    kag_query: Annotated[Optional[str], overwrite_reducer]
    kag_results: Annotated[Optional[List[Any]], overwrite_reducer]
    
    # 리랭킹 결과
    rerank_results: Annotated[Optional[List[Any]], overwrite_reducer]
    
    # 최종 결과
    final_results: Annotated[Optional[List[Any]], overwrite_reducer]
    final_recommendation: Annotated[Optional[str], overwrite_reducer]
    
    # 추천된 상품 ID 목록
    product_ids: Annotated[Optional[List[Dict[str, Any]]], overwrite_reducer]
    
    # Human-in-the-loop 관련 필드
    needs_human_input: Annotated[bool, overwrite_reducer]
    human_input_request: Annotated[Optional[str], overwrite_reducer]
    followup_question: Annotated[Optional[str], overwrite_reducer]
    
    # 영양소 지식 검색 결과
    nutrient_knowledge: Annotated[Optional[NutrientKnowledge], merge_dict]
    nutrient_summary: Annotated[Optional[NutrientSummary], merge_dict]
    
    # 추가 메타데이터
    metadata: Annotated[Dict[str, Any], merge_dict]

    state: Annotated[Dict[str, Any], "state"]