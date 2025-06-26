from typing import Dict, Any

from ...state import AgentState
from Product.models import Products
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../..'))
from recommendation.total_recommendation import TotalRecommender

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
    user_id = state.get("user_id")
    
    print(f"\n=== 리랭킹 시작 ===")
    print(f"입력된 kag_results 개수: {len(kag_results)}")
    print(f"사용자 ID: {user_id}")
    
    # kag_results에서 id만 추출
    id_list = [item.get('id') for item in kag_results if 'id' in item]
    
    # TotalRecommender에 전달할 파라미터를 JSON 형태로 구성
    recommender_params = {
        "user_id": user_id,
        "product_ids": id_list
    }
    
    print(f"TotalRecommender 파라미터: {recommender_params}")
    
    # TotalRecommender 초기화 및 추천 실행
    try:
        total_recommender = TotalRecommender(recommender_params)
        recommended_ids, recommend_type = total_recommender()
        
        print(f"추천 타입: {recommend_type}")
        print(f"추천된 상품 ID 리스트: {recommended_ids}")
        
        reranked_results = recommended_ids
        
        print(f"최종 reranked_results: {reranked_results}")
        print(f"=== 리랭킹 완료({recommend_type} 추천 기준) ===\n")
        
        node_messages.append(f"rerank_node 노드: '{recommend_type} 추천 모델을 사용하여 주어진 상품 리스트 재순위화를 완료했습니다.'")
        
    except Exception as e:
        print(f"TotalRecommender 실행 중 오류 발생: {e}")
        print("기존 popularity_score 기준으로 정렬을 진행합니다.")
        
        # 오류 발생 시 기존 로직으로 fallback
        pre_products = Products.objects.filter(id__in=id_list)
        pre_id_score = [(p.id, p.popularity_score) for p in pre_products]
        print(f"정렬 전 id와 popularity_score: {pre_id_score}")
        
        products = Products.objects.filter(id__in=id_list).order_by('-popularity_score')
        sorted_id_list = [product.id for product in products]
        id_to_item = {item['id']: item for item in kag_results if 'id' in item}
        reranked_results = [id_to_item[pid] for pid in sorted_id_list if pid in id_to_item]
        
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