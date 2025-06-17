from typing import Dict, Any, List
import json

from ...state import AgentState
from ..base import get_llm_json_response

from langgraph.errors import NodeInterrupt

# def extract_health_info(state: AgentState) -> Dict[str, Any]:
#     """
#     사용자 입력에서 건강 정보를 추출하여 기존 설문조사 데이터를 업데이트하는 함수
    
#     Args:
#         state: 현재 에이전트 상태
        
#     Returns:
#         변경된 상태 필드만 포함하는 딕셔너리
#     """
#     print("건강 정보를 추출할게요!")
#     # 가장 최근 사용자 메시지 추출
#     messages = state.get("messages", [])
#     if not messages:
#         return {}
    
#     latest_message = messages[-1]
#     if latest_message.type != "human":
#         return {}
    
#     user_query = latest_message.content
#     current_health_data = state.get("user_health_info", {})
    
#     # 시스템 프롬프트 정의
#     system_prompt = f"""당신은 건강 정보 추출 전문가입니다.

# **임무**: 사용자의 입력에서 건강 관련 정보를 추출하여 기존 설문조사 데이터를 업데이트하세요.

# **현재 설문조사 데이터**:
# ```json
# {json.dumps(current_health_data, ensure_ascii=False, indent=2)}
# ```

# **지침**:
# 1. 사용자 입력에서 설문조사 항목과 관련된 정보만 추출하세요.
# 2. 기존 데이터를 수정하거나 새로운 정보를 추가하세요.
# 3. 확실하지 않은 정보는 추가하지 마세요.
# 4. 알레르기 정보는 리스트에 추가하세요 (기존 항목 유지).
# 5. 약물 정보도 리스트에 추가하세요 (기존 항목 유지).

# **응답 형식**:
# 다음과 같은 JSON 형태로 응답하세요:
# {{
#   "updated_health_info": {{업데이트된 전체 건강 정보}},
#   "extracted_changes": {{
#     "category": "변경된 카테고리",
#     "field": "변경된 필드명",
#     "old_value": "기존 값",
#     "new_value": "새로운 값",
#     "action": "add|update|remove"
#   }}
# }}"""

#     # LLM에 요청하여 건강 정보 추출
#     result = get_llm_json_response(
#         system_prompt=system_prompt,
#         user_prompt=user_query
#     )
    
#     updated_health_info = result.get("updated_health_info", current_health_data)
    
#     # 변경된 상태 필드만 반환
#     return {"user_health_info": updated_health_info}

def extract_supplement_info(state: AgentState) -> Dict[str, Any]:
    """
    사용자 쿼리에서 영양제 관련 정보를 추출하는 함수
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    # 가장 최근 사용자 메시지 추출
    messages = state.get("messages", [])
    if not messages:
        return {}
    
    latest_message = messages[-1]
    if latest_message.type != "human":
        return {}
    
    user_query = latest_message.content
    
    # 추출할 정보를 위한 카테고리 리스트 정의
    nutrient_lst = [
        "비타민 A", "베타카로틴", "비타민 D", "비타민 E", "비타민 K", "비타민 B1", "비타민 B2",
        "나이아신", "판토텐산", "비타민 B6", "엽산", "비타민 B12", "비오틴", "비타민 C", "칼슘", "마그네슘",
        "철", "아연", "구리", "셀레늄", "요오드", "망간", "몰리브덴", "칼륨", "크롬", "루테인", "인",
        "메티오닌", "시스테인", "류신", "트립토판", "라이신", "트레오닌", "페닐알라닌", "티로신", "오메가3"
    ]

    taste_lst = [
        "오렌지", "복숭아", "베리", "망고", "체리", "딸기", "파인애플",
        "바나나", "멜론", "포도", "사과", "키위", "수박"
    ]

    type_lst = [
        "비타민 A", "베타카로틴", "비타민 D", "비타민 E", "비타민 K", "비타민 B1", "비타민 B2",
        "나이아신", "판토텐산", "비타민 B6", "엽산", "비타민 B12", "비오틴", "비타민 C", "칼슘", "마그네슘",
        "철", "아연", "구리", "셀레늄", "요오드", "망간", "몰리브덴", "칼륨", "크롬", "루테인", "인",
        "메티오닌", "시스테인", "류신", "트립토판", "라이신", "트레오닌", "페닐알라닌", "티로신", "멀티비타민"
    ]

    form_lst = [
        "알약", "캡슐", "젤리", "분말", "젤", "캔디", "액상"
    ]

    purpose_tag_lst = [
        "간", "기분", "근육", "눈", "면역", "뼈", "소화",
        "수면", "수분", "신경", "성장", "집중", "피부", "혈당",
        "혈액", "항산화", "해독", "피로회복"
    ]
    
    # 시스템 프롬프트 정의
    system_prompt = f"""당신은 사용자의 영양제 관련 텍스트에서 다양한 정보를 추출하는 전문가입니다.

사용자 텍스트를 분석하여 다음 정보들을 추출해주세요:

1. **영양소**: {', '.join(nutrient_lst)}
2. **맛**: {', '.join(taste_lst)}
3. **영양제 종류**: {', '.join(type_lst)}
4. **양식**: {', '.join(form_lst)}
5. **건강 목적**: {', '.join(purpose_tag_lst)}
6. **수량**: 영양제 개수 관련 숫자만 (함유량 제외)
7. **가격**: 가격 범위나 조건 (예: "2만원 이하", "저렴한")
8. **원산지**: 국가명이나 지역명
9. **별점 선호도**: 높은 별점순을 원하는지 (true/false/null)
10. **리뷰수 선호도**: 많은 리뷰수순을 원하는지 (true/false/null)
11. **비건 선호도**: 비건 제품을 원하는지 (true/false/null)

**추출 규칙:**
- 명시적으로 언급된 항목만 추출
- 정확한 이름으로 매칭 (예: "비타민C" → "비타민 C")
- 리스트에 없는 항목은 포함하지 말것
- 영양제 종류는 질문의 맥락을 파악하여 추출하세요. 단순 영양소인지, 영양제 유형을 원하는지 파악해야합니다.
  - 예시: 비타민 C를 보충하고싶어. -> 미포함
  - 예시: 비타민 C 영양제를 추천해줘. -> 비타민 C 포함
- 불린 값: true(원함), false(명시적 거부), null(언급 없음)

**응답 형식 (JSON):**
{{
  "nutrients": ["항목1", "항목2"],
  "flavors": ["항목1", "항목2"],
  "supplement_types": ["항목1", "항목2"],
  "forms": ["항목1", "항목2"],
  "purpose_tag": ["항목1", "항목2"],
  "quantities": ["30", "60"],
  "prices": ["2만원 이하", "저렴한"],
  "origins": ["미국", "독일"],
  "order_ratings": true/false/null,
  "order_reviewcnt": true/false/null,
  "is_vegan": true/false/null
}}"""

    # LLM에 요청하여 영양제 정보 추출
    result = get_llm_json_response(
        system_prompt=system_prompt,
        user_prompt=user_query
    )
    print(result)
    
    # 필수 정보가 있는지 확인 (영양소 또는 목적 태그 중 하나는 필수)
    nutrients = result.get("nutrients", [])
    purpose_tags = result.get("purpose_tag", [])
    
    if not nutrients and not purpose_tags:
        request_more_info = get_llm_json_response(
            system_prompt="당신은 영양제와 영양소에 관한 전문 지식을 갖춘 친절한 챗봇입니다. 사용자에게 영양제를 섭취하려는 목적, 어떤 영양소를 섭취하려는지 물어보는 질문을 작성해주세요.",
            user_prompt=user_query,
            response_format_json=False
        )

        print(f"정보 부족으로 interrupt 발생: {request_more_info}")

        # NodeInterrupt를 직접 발생시켜서 워크플로우 중단
        raise NodeInterrupt(request_more_info)
    
    # 추출된 정보에서 has_sufficient_info 키 제거
    if "has_sufficient_info" in result:
        del result["has_sufficient_info"]
    
    print(f"충분한 정보 추출됨: {result}")

    # 변경된 상태 필드만 반환
    return {
        "extracted_info": result,
        "needs_human_input": False
    } 