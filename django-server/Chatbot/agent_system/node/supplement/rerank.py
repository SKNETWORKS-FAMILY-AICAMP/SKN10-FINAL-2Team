from typing import Dict, Any

from ...state import AgentState
from Product.models import Products

def rerank_node(state: AgentState) -> Dict[str, Any]:
    """
    검색된 영양제 결과를 사용자 요구사항에 맞게 재순위화하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    node_messages = state.get("node_messages", [])

    # 필요한 정보 가져오기
    kag_results = state.get("kag_results", [])
    
    print(f"\n=== 리랭킹 시작 ===")
    print(f"입력된 kag_results 개수: {len(kag_results)}")
    
    # kag_results에서 id만 추출
    id_list = [item.get('id') for item in kag_results if 'id' in item]
    # 정렬 전 id와 popularity_score 출력
    pre_products = Products.objects.filter(id__in=id_list)
    pre_id_score = [(p.id, p.popularity_score) for p in pre_products]
    print(f"정렬 전 id와 popularity_score: {pre_id_score}")
    # Products에서 해당 id의 객체들을 popularity_score 기준으로 내림차순 정렬
    products = Products.objects.filter(id__in=id_list).order_by('-popularity_score')
    # 정렬된 products의 id 순서대로 kag_results 재정렬
    sorted_id_list = [product.id for product in products]
    id_to_item = {item['id']: item for item in kag_results if 'id' in item}
    reranked_results = [id_to_item[pid] for pid in sorted_id_list if pid in id_to_item]
    # 정렬 후 id와 popularity_score 출력
    post_id_score = [(p.id, p.popularity_score) for p in products]
    print(f"정렬 후 id와 popularity_score: {post_id_score}")
    print(f"최종 reranked_results: {reranked_results}")
    print("=== 리랭킹 완료(popularity_score 기준) ===\n")

    node_messages.append("rerank_node 노드: '비개인화 추천 모델을 사용하여 주어진 상품 리스트 재순위화를 완료했습니다.'")
    
    # 변경된 상태 필드만 반환
    return {
        "rerank_results": reranked_results,
        "node_messages": node_messages
    }

def select_products_node(state: AgentState) -> Dict[str, Any]:
    """
    재순위화된 결과에서 최종 추천 제품을 선택하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    node_messages = state.get("node_messages", [])

    # 재순위화된 결과 가져오기
    rerank_results = state.get("rerank_results", [])
    
    print(f"\n=== 최종 제품 선택 ===")
    print(f"입력된 rerank_results 개수: {len(rerank_results)}")
    
    final_results = rerank_results
    print("=== 최종 제품 선택 완료 ===\n")

    node_messages.append("select_products_node 노드: '순위가 높은 상품만을 선택하였습니다.'")
    
    # 변경된 상태 필드만 반환
    return {"final_results": final_results} 