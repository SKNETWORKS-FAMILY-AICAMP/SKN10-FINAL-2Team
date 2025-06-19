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
    user_health_info = state.get("user_health_info", {})
    
    print(f"\n=== 리랭킹 시작 ===")
    print(f"입력된 kag_results 개수: {len(kag_results)}")
    
#     if not kag_results:
#         return {"rerank_results": []}
    
#     # 시스템 프롬프트 정의
#     system_prompt = """당신은 영양제 추천 전문가입니다.
# 검색된 영양제 목록을 사용자의 요구사항과 건강 정보에 맞게 재순위화해주세요.

# 중요: 입력받은 모든 영양제를 반드시 포함해야 합니다. 상품을 누락하거나 제거하지 마세요.

# 재순위화 기준:
# 1. 사용자가 요청한 영양소를 포함하는 제품 우선
# 2. 사용자의 건강 목적에 맞는 제품 우선
# 3. 사용자가 선호하는 형태, 맛, 원산지 등 고려
# 4. 사용자의 건강 상태(피로, 눈, 성장, 수면 등) 고려
# 5. 가격 대비 효용성
# 6. 평점과 리뷰 수

# JSON 형식으로 다음 정보를 반환해주세요:
# {
#   "reranked_results": [
#     {
#       "id": "제품 ID",
#       "name": "제품명",
#       "rating": 평점,
#       "review_count": 리뷰 수,
#       "is_vegan": 비건 여부,
#       "total_price": 가격,
#       "quantity": "수량",
#       "rank_score": 순위 점수(0-100),
#       "rank_reason": "순위 부여 이유"
#     },
#     ...
#   ]
# }"""

#     # 사용자 프롬프트 구성
#     user_prompt = f"""영양제 검색 결과 (총 {len(kag_results)}개):
# {json.dumps(kag_results, ensure_ascii=False, indent=2)}

# 추출된 사용자 요구사항:
# {json.dumps(extracted_info, ensure_ascii=False, indent=2)}

# 사용자 건강 설문조사 정보:
# {json.dumps(user_health_info, ensure_ascii=False, indent=2)}

# 위 정보를 바탕으로 검색된 모든 영양제 결과를 재순위화해주세요. 
# 반드시 입력받은 {len(kag_results)}개의 모든 영양제를 포함해야 합니다."""

#     # LLM에 요청하여 결과 재순위화
#     result = get_llm_json_response(
#         system_prompt=system_prompt,
#         user_prompt=user_prompt
#     )
    
#     print(f"LLM 응답 결과: {result}")
    
#     reranked_results = result.get("reranked_results", [])
#     print(f"LLM이 반환한 reranked_results 개수: {len(reranked_results)}")
    
#     # 상품 개수가 줄어든 경우 원본 결과 사용
#     if len(reranked_results) < len(kag_results):
#         print(f"⚠️ 경고: 상품 개수가 줄어들었습니다. 원본 결과를 사용합니다.")
#         print(f"원본: {len(kag_results)}개, LLM 결과: {len(reranked_results)}개")
    
#     # rank_score 기준으로 내림차순 정렬
#     if reranked_results and isinstance(reranked_results[0], dict) and 'rank_score' in reranked_results[0]:
#         reranked_results.sort(key=lambda x: x.get('rank_score', 0), reverse=True)
#         print(f"rank_score 기준으로 정렬 완료")
    reranked_results = kag_results
    print(f"최종 reranked_results 개수: {len(reranked_results)}")
    print("=== 리랭킹 완료(안함) ===\n")
    
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
    
    print(f"\n=== 최종 제품 선택 ===")
    print(f"입력된 rerank_results 개수: {len(rerank_results)}")
    
    # # 상위 20개의 제품만 선택 (이미 rank_score 기준으로 정렬되어 있음)
    # final_results = rerank_results[:20]
    
    # print(f"최종 선택된 제품 개수: {len(final_results)}")
    # if final_results and isinstance(final_results[0], dict) and 'rank_score' in final_results[0]:
    #     print(f"상위 3개 제품의 rank_score: {[item.get('rank_score', 'N/A') for item in final_results[:3]]}")
    final_results = rerank_results
    print("=== 최종 제품 선택 완료 ===\n")
    
    # 변경된 상태 필드만 반환
    return {"final_results": final_results} 