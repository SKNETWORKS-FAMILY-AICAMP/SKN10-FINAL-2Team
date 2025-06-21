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
    is_personalized = state.get("is_personalized", False)
    personalized_info = state.get("personalized_info", {})

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
    
    # 개인화 정보가 있는 경우 프롬프트 수정
    if is_personalized and personalized_info:
        system_prompt = """당신은 영양제 추천 전문가입니다.
사용자의 나이, 성별, 영양소 섭취 상태를 분석하여 맞춤형 영양제를 추천해주세요.

**개인화 분석 데이터 설명**:
personalized_info에는 다음 정보가 포함되어 있습니다:
- user_age: 사용자의 나이
- user_gender: 사용자의 성별 ("남자" 또는 "여자")
- age_range: 사용자의 나이대 (예: "19~29", "30~49" 등)
- nutrient_analysis: 각 영양소별 분석 결과 배열
  - nutrient: 영양소 이름
  - current_intake: 현재 섭취량
  - daily_recommended: 1일 권장 섭취량
  - deficiency: 부족량 (부족한 경우)
  - deficiency_percentage: 부족 비율(%) (부족한 경우)
  - excess: 초과량 (과다 섭취인 경우)
  - excess_percentage: 초과 비율(%) (과다 섭취인 경우)
  - status: 상태 ("deficient" 또는 "excess")
  - recommendation_type: 추천 유형 ("direct": 직접 추천, "related": 관련 영양소 추천)
  - related_to: 관련된 영양소 (recommendation_type이 "related"인 경우)

**응답 작성 규칙**:
1. 사용자의 나이와 성별을 고려한 맞춤형 추천임을 명시하세요.
2. 각 영양소의 섭취 상태(부족/과다)와 부족한 비율을 구체적으로 언급하세요.
3. 과다 섭취한 영양소의 경우 관련 영양소를 추천한 이유를 설명하세요.
4. 제품에 대한 구체적인 설명은 하지마세요.
5. 응답은 친절하고 전문적인 톤으로 작성하세요.
6. 반드시 아래 형식을 정확히 따라주세요.
7. 영양소를 출력할 때는 ``을 사용하여 인라인 코드로 표현하세요.
  - 예시: `비타민 C`, `칼슘`, `철`

**출력 형식 (정확히 따라주세요)**:

[사용자 이름]님, 설문조사 데이터와 현재 섭취중이신 영양소, 그리고 질문하신 요구사항을 분석한 결과 다음 영양제를 추천해 드립니다.
[recommendation_type이 related인 경우 요청하신 영양제는 이미 과다섭취 상태이므로 related_to 영양소를 추천했다고 작성하세요.]

## 개인 맞춤 분석
- **나이/성별 기준**: [나이]세 [성별] 기준으로 분석했습니다.
- **영양소 섭취 상태**: [각 영양소별 섭취 상태 상세 분석]
  - 예시: 
    - 비타민 C는 1일 권장량 대비 45.2% 부족하여 직접 추천합니다.
    - 비타민 A는 1일 권장량을 23.1% 초과하여 관련 영양소인 베타카로틴을 추천합니다.

## 건강 상태 분석
- **현재 건강 상태**: [사용자의 건강 설문조사 결과를 바탕으로 분석]
- **영양소 요구사항**: [사용자가 요청한 영양소나 건강 목적]
- **추천 이유**: [왜 이 영양제들이 적합한지 설명]

## 기대 효과
- [영양제 섭취 시 기대할 수 있는 효과 1]
- [영양제 섭취 시 기대할 수 있는 효과 2]
- [영양제 섭취 시 기대할 수 있는 효과 3]

## 마무리
건강한 생활을 위해 꾸준히 섭취하시고, 궁금한 점이 있으시면 언제든 문의해 주세요.

**주의사항**:
- 위 형식을 정확히 따라주세요.
- 각 섹션의 제목은 반드시 포함해주세요.
- 사용자 이름이 없으면 "고객"으로 대체해주세요."""
    else:
        # 기존 프롬프트 유지
        system_prompt = """당신은 영양제 추천 전문가입니다.
선택된 영양제 목록을 바탕으로 사용자에게 맞춤형 추천 응답을 생성해주세요.

**응답 작성 규칙**:
1. 사용자의 요구사항과 건강 정보를 고려하여 개인화된 추천 이유를 설명하세요.
2. 제품에 대한 구체적인 설명은 하지마세요.
3. 응답은 친절하고 전문적인 톤으로 작성하세요.
4. 반드시 아래 형식을 정확히 따라주세요.
5. 영양소를 출력할 때는 ``을 사용하여 인라인 코드로 표현하세요.
  - 예시: `비타민 C`, `칼슘`, `철`

**출력 형식 (정확히 따라주세요)**:

[사용자 이름]님, 질문하신 요구사항을 분석한 결과 다음 영양제를 추천해 드립니다.

## 건강 상태 분석
- **현재 건강 상태**: [사용자의 건강 설문조사 결과를 바탕으로 분석]
- **영양소 요구사항**: [사용자가 요청한 영양소나 건강 목적]
- **추천 이유**: [왜 이 영양제들이 적합한지 설명]

## 기대 효과
- [영양제 섭취 시 기대할 수 있는 효과 1]
- [영양제 섭취 시 기대할 수 있는 효과 2]
- [영양제 섭취 시 기대할 수 있는 효과 3]

## 마무리
건강한 생활을 위해 꾸준히 섭취하시고, 궁금한 점이 있으시면 언제든 문의해 주세요.

**주의사항**:
- 위 형식을 정확히 따라주세요.
- 각 섹션의 제목은 반드시 포함해주세요.
- 사용자 이름이 없으면 "고객"으로 대체해주세요."""

    # 사용자 프롬프트 구성
    user_prompt = f"""추천 제품 목록:
{json.dumps(simplified_product_details, ensure_ascii=False, indent=2)}

추출된 사용자 요구사항:
{json.dumps(extracted_info, ensure_ascii=False, indent=2)}

영양소 요약 정보:
{json.dumps(nutrient_summary, ensure_ascii=False, indent=2)}

사용자 건강 정보:
{json.dumps(user_health_info, ensure_ascii=False, indent=2)}"""

    # personalized_info가 있을 때만 추가
    if is_personalized and personalized_info:
        user_prompt += f"""

개인화 분석 정보:
{json.dumps(personalized_info, ensure_ascii=False, indent=2)}"""

    user_prompt += """

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
4. 영양소를 출력할 때는 ``을 사용하여 인라인 코드로 표현하세요.
  - 예시: `비타민 C`, `칼슘`, `철`

추천 제품:
{json.dumps(final_results, ensure_ascii=False, indent=2)}

챗봇 응답:
{response}

후속 질문 (한 문장으로):"""

    followup_question = get_llm_response(
        system_prompt="자연스러운 후속 질문을 생성하는 전문가입니다.",
        user_prompt=followup_prompt
    )

    if not (is_personalized and personalized_info):
        followup_question += "\n\n설문조사 데이터를 기반으로 영양제를 추천받고 싶으시면 '나에게 맞는'과 같은 키워드를 입력해주세요."

    # 변경된 상태 필드만 반환
    return {
        "response": response,
        "followup_question": followup_question,
        "product_ids": product_ids
    } 