from typing import Dict, Any
import json

from ...state import AgentState
from ..base import get_llm_response

from Product.models import Products

def generate_supplement_response(state: AgentState) -> Dict[str, Any]:
    """
    영양제 추천 결과를 바탕으로 사용자에게 응답을 생성하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    # 필요한 정보 가져오기
    final_results = state.get("final_results", [])
    extracted_info = state.get("extracted_info", {})
    nutrient_summary = state.get("nutrient_summary", {})
    user_health_info = state.get("user_health_info", {})

    if not final_results:
        # 검색 결과가 없는 경우
        return {
            "final_recommendation": "죄송합니다. 요청하신 조건에 맞는 영양제를 찾을 수 없습니다. 조건을 조정해서 다시 검색해보시겠어요?",
            "followup_question": "어떤 영양소와 건강 목적에 관심이 있으신가요?"
        }
    print("final_result:", final_results)
    product_ids = []
    simplified_product_details = []
    for result in final_results:
        product_id = result.get('id')
        product_ids.append(product_id)
        product = Products.objects.get(id=product_id)
        simplified_product_details.append({
            'title': product.title,
            'brand': product.brand,
            'average_rating': product.average_rating,
            'total_reviews': product.total_reviews,
            'ingredients': product.ingredients,
            'supplement_type': product.supplement_type,
            'product_form': product.product_form,
            'vegan': product.vegan,
            'directions': product.directions,
            'safety_info': product.safety_info
        })
    
    # 시스템 프롬프트 정의
    system_prompt = """당신은 영양제 추천 전문가입니다.
선택된 영양제 목록을 바탕으로 사용자에게 맞춤형 추천 응답을 생성해주세요.

응답 작성 지침:
1. 사용자의 요구사항과 건강 정보를 고려하여 개인화된 추천 이유를 설명하세요.
2. 제품에 대한 설명은 하지마세요.
3. 응답은 친절하고 전문적인 톤으로 작성하세요.

**출력 형식(마크다운)**:
1. 인사말: "[사용자 이름]님, 건강 상태와 요구사항을 분석한 결과 다음 영양제를 추천해 드립니다." 로 시작하세요.
2. 추천 이유:
   - 사용자의 건강 상태 분석 결과
   - 요구사항과의 부합도
   - 기대 효과
3. 마무리 문장"""

    # 사용자 프롬프트 구성
    user_prompt = f"""추천 제품 목록:
{json.dumps(simplified_product_details, ensure_ascii=False, indent=2)}

추출된 사용자 요구사항:
{json.dumps(extracted_info, ensure_ascii=False, indent=2)}

영양소 요약 정보:
{json.dumps(nutrient_summary, ensure_ascii=False, indent=2)}

사용자 건강 정보:
{json.dumps(user_health_info, ensure_ascii=False, indent=2)}

위 정보를 바탕으로 사용자에게 맞춤형 영양제 추천 응답을 생성해주세요."""

    # LLM에 요청하여 응답 생성
    response = get_llm_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    # 후속 질문 생성
    followup_prompt = f"""사용자와의 대화를 바탕으로 자연스러운 후속 질문을 1개만 생성해주세요.
후속 질문은 다음 중 하나를 목적으로 해야 합니다:
1. 추천 제품에 대한 추가 정보 제공
2. 다른 영양소나 건강 목적에 대한 추천 제안
3. 사용자의 건강 관리에 대한 추가 조언

추천 제품:
{json.dumps(final_results, ensure_ascii=False, indent=2)}

챗봇 응답:
{response}

후속 질문 (한 문장으로):"""

    followup_question = get_llm_response(
        system_prompt="자연스러운 후속 질문을 생성하는 전문가입니다.",
        user_prompt=followup_prompt
    )
    
    # 변경된 상태 필드만 반환
    return {
        "final_recommendation": response,
        "followup_question": followup_question,
        "product_ids": product_ids
    } 