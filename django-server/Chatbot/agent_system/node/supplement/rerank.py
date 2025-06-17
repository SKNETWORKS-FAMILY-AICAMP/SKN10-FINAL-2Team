from typing import Dict, Any, List
import json

from ...state import AgentState
from ..base import get_llm_json_response

def rerank_node(state: AgentState) -> Dict[str, Any]:
    """
    검색된 영양제 결과를 사용자 요구사항에 맞게 재순위화하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    # 필요한 정보 가져오기
    kag_results = state.get("kag_results", [])
    extracted_info = state.get("extracted_info", {})
    nutrient_summary = state.get("nutrient_summary", {})
    user_health_info = state.get("user_health_info", {})
    
    if not kag_results:
        return {"rerank_results": []}
    
    # 시스템 프롬프트 정의
    system_prompt = """당신은 영양제 추천 전문가입니다.
검색된 영양제 목록을 사용자의 요구사항과 건강 정보에 맞게 재순위화해주세요.

재순위화 기준:
1. 사용자가 요청한 영양소를 포함하는 제품 우선
2. 사용자의 건강 목적에 맞는 제품 우선
3. 사용자가 선호하는 형태, 맛, 원산지 등 고려
4. 사용자의 건강 상태(알레르기, 약물 상호작용 등) 고려
5. 가격 대비 효용성
6. 평점과 리뷰 수

JSON 형식으로 다음 정보를 반환해주세요:
{
  "reranked_results": [
    {
      "id": "제품 ID",
      "name": "제품명",
      "rating": 평점,
      "review_count": 리뷰 수,
      "is_vegan": 비건 여부,
      "total_price": 가격,
      "quantity": "수량",
      "rank_score": 순위 점수(0-100),
      "rank_reason": "순위 부여 이유"
    },
    ...
  ]
}"""

    # 사용자 프롬프트 구성
    user_prompt = f"""검색 결과:
{json.dumps(kag_results, ensure_ascii=False, indent=2)}

추출된 사용자 요구사항:
{json.dumps(extracted_info, ensure_ascii=False, indent=2)}

영양소 요약 정보:
{json.dumps(nutrient_summary, ensure_ascii=False, indent=2)}

사용자 건강 정보:
{json.dumps(user_health_info, ensure_ascii=False, indent=2)}

위 정보를 바탕으로 검색된 영양제 결과를 재순위화해주세요."""

    # LLM에 요청하여 결과 재순위화
    result = get_llm_json_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    reranked_results = result.get("reranked_results", kag_results)
    
    # 변경된 상태 필드만 반환
    return {"rerank_results": reranked_results}

def select_products_node(state: AgentState) -> Dict[str, Any]:
    """
    재순위화된 결과에서 최종 추천 제품을 선택하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    # 재순위화된 결과 가져오기
    rerank_results = state.get("rerank_results", [])
    
    # 최대 5개의 제품만 선택
    final_results = rerank_results[:5] if len(rerank_results) > 5 else rerank_results
    
    # 변경된 상태 필드만 반환
    return {"final_results": final_results} 