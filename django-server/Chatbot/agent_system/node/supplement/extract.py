from typing import Dict, Any, List
import json

from ...state import AgentState
from ..base import get_llm_json_response


def is_personalized_supplement(state: AgentState) -> Dict[str, Any]:
    """
    사용자 입력을 분석하여 개인화/비개인화 추천 유형을 결정하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """

    print("개인화 여부 판단을 시작했어요!")
    node_messages = state.get("node_messages", [])

    # 가장 최근 사용자 메시지 추출
    messages = state.get("messages", [])
    if not messages:
        return {"conversation_type": "general"}
    
    latest_message = messages[-1]
    if latest_message.type != "human":
        return {"conversation_type": "general"}
    
    user_query = latest_message.content
    
    # 시스템 프롬프트 정의
    system_prompt = """당신은 사용자의 메시지를 분석하여 개인화된 영양제 추천 여부를 판단하는 전문가입니다. 각 메시지를 다음 기준에 따라 정확하게 분류해주세요.

[개인화 여부 판단]
- True: 사용자가 자신에게 맞는 맞춤형 추천을 요청한 경우(사용자의 입력에 '나에게 맞는', '저에게 맞는' 이라는 키워드가 있는 경우만 True입니다.)
  예시: "나에게 맞는 영양제를 추천해주세요", "저에게 맞는 비타민을 찾고 싶어요"
- False: 일반적인 제품 추천 요청(사용자의 입력에 '나에게 맞는', '저에게 맞는' 이라는 키워드가 없는 경우 모두 False입니다.)
  예시: "비타민 C 영양제 추천해주세요", "피로회복에 좋은 영양제 알려주세요"

[응답 형식]
다음 JSON 형식으로 응답해주세요:
{
  "is_personalized": true | false,
}"""

    # LLM에 요청하여 대화 유형 분류
    result = get_llm_json_response(
        system_prompt=system_prompt,
        user_prompt=user_query
    )

    is_personalized = result.get("is_personalized", False)

    if is_personalized:
        node_messages.append("is_personalized_supplement 노드: '사용자가 설문조사 및 영양소 섭취량을 고려한 개인화된 영양제 상품 검색 및 추천을 원한다고 판단되었습니다.'")
    elif not is_personalized:
        node_messages.append("is_personalized_supplement 노드: '사용자가 일반적인 영양제 상품 검색 및 추천을 원한다고 판단되었습니다.'")
    else:
        node_messages.append("is_personalized_supplement 노드: '오류가 발생했습니다. 이 메세지는 무시하세요.'")

    print("개인화 여부 판단이 끝났어요!", is_personalized)
    return {
        "is_personalized": is_personalized,
        "node_messages": node_messages
    } 


def is_enough_supplement_info(state: AgentState) -> Dict[str, Any]:
    """
    사용자 쿼리에서 영양제 관련 정보를 추출하는 함수
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    print("영양소, 건강 목적을 추출합니다!")

    node_messages = state.get("node_messages", [])

    # 가장 최근 사용자 메시지 추출
    messages = state.get("messages", [])
    if not messages:
        return {}
    
    latest_message = messages[-1]
    if latest_message.type != "human":
        return {}
    
    user_query = latest_message.content

    nutrient_lst = [
        "비타민 A", "베타카로틴", "비타민 D", "비타민 E", "비타민 K", "비타민 B1", "비타민 B2",
        "나이아신", "판토텐산", "비타민 B6", "엽산", "비타민 B12", "비오틴", "비타민 C", "칼슘", "마그네슘",
        "철", "아연", "구리", "셀레늄", "요오드", "망간", "몰리브덴", "칼륨", "크롬", "루테인", "인",
        "메티오닌", "시스테인", "류신", "트립토판", "이소류신", "라이신", "트레오닌", "페닐알라닌", "티로신"
    ]

    purpose_tag_lst = [
        "간", "기분", "근육", "눈", "면역", "뼈", "소화",
        "수면", "수분", "신경", "성장", "집중", "피부", "혈당",
        "혈액", "항산화", "해독", "피로회복"
    ]

    type_lst = [
        "비타민 A", "베타카로틴", "비타민 D", "비타민 E", "비타민 K", "비타민 B1", "비타민 B2",
        "나이아신", "판토텐산", "비타민 B6", "엽산", "비타민 B12", "비오틴", "비타민 C", "칼슘", "마그네슘",
        "철", "아연", "구리", "셀레늄", "요오드", "망간", "몰리브덴", "칼륨", "크롬", "루테인", "인",
        "메티오닌", "시스테인", "류신", "트립토판", "이소류신", "라이신", "트레오닌", "페닐알라닌", "티로신", "멀티비타민"
    ]

        # 시스템 프롬프트 정의
    system_prompt = f"""당신은 사용자의 영양제 관련 텍스트에서 다양한 정보를 추출하는 전문가입니다.

사용자 텍스트를 분석하여 다음 정보들을 추출해주세요:

1. **영양소**: {', '.join(nutrient_lst)}
2. **건강 목적**: {', '.join(purpose_tag_lst)}
3. **영양제 종류**: {', '.join(type_lst)}

**추출 규칙:**
- 명시적으로 언급된 항목만 추출
- 정확한 이름으로 매칭 (예: "비타민C" → "비타민 C")
- 리스트에 없는 항목은 포함하지 말것
- 영양제 종류는 질문의 맥락을 파악하여 추출하세요. 단순 영양소인지, 영양제 유형을 원하는지 파악해야합니다.
  - 예시: 비타민 C를 보충하고싶어. -> 미포함
  - 예시: 비타민 C 영양제를 추천해줘. -> 비타민 C 포함

**응답 형식 (JSON):**
{{
  "nutrients": ["항목1", "항목2"],
  "purpose_tag": ["항목1", "항목2"],
  "supplement_types": ["항목1", "항목2"]
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
    supplement_types = result.get("supplement_types", [])

    # LLM 결과값이 실제 리스트에 존재하는 값인지 검증
    valid_nutrients = [n for n in nutrients if n in nutrient_lst]
    valid_purpose_tags = [p for p in purpose_tags if p in purpose_tag_lst]
    valid_supplement_types = [t for t in supplement_types if t in type_lst]

    # 만약 유효하지 않은 값이 있다면 로그로 출력
    invalid_nutrients = [n for n in nutrients if n not in nutrient_lst]
    invalid_purpose_tags = [p for p in purpose_tags if p not in purpose_tag_lst]
    invalid_supplement_types = [t for t in supplement_types if t not in type_lst]

    if invalid_nutrients or invalid_purpose_tags or invalid_supplement_types:
        print(f"유효하지 않은 영양소: {invalid_nutrients}")
        print(f"유효하지 않은 목적 태그: {invalid_purpose_tags}")
        print(f"유효하지 않은 영양제 종류: {invalid_supplement_types}")

    # 이후 valid 값만 사용
    nutrients = valid_nutrients
    purpose_tags = valid_purpose_tags
    supplement_types = valid_supplement_types

    # result 딕셔너리에 업데이트
    result["nutrients"] = nutrients
    result["purpose_tag"] = purpose_tags
    result["supplement_types"] = supplement_types

    if not(nutrients or purpose_tags or supplement_types):
        response = get_llm_json_response(
            system_prompt=f"""당신은 영양제와 영양소에 관한 전문 지식을 갖춘 친절한 챗봇 '영양이'입니다.
영양소, 영양제와 관련없는 질문은 대답하지 마세요.
사용자에게 영양제를 섭취하려는 건강 목적, 어떤 영양소를 섭취하려는지 물어보는 질문을 작성해주세요.
현재 사용자는 어떤 영양소에 대해 설명이 필요한건지 정확히 제시하지 않은 상태입니다.

사용자의 사전 설문조사 내용을 참고한 후, 어떤 영양소, 어떤 건강 목적을 대답할 수 있는지 사용자에게 추천할 만한 예시를 각 5개 이하만 전달하세요.
만약 사용자가 영양소 예시 목록에 없는 영양소를 원하는 경우, 영양소 예시 목록에 있는 영양소 중 유사한 영양소를 추천해주세요.
반드시 영양소 예시, 건강 목적 예시 목록에 있는 예시만 전달하세요.
예를 들어, 사전 설문 조사 결과에서 "낮에 주로 실내에서 활동하시나요"에 "예"라고 답했다면, 비타민 D 영양소를 추천할 수 있습니다.
"잠을 자도 피곤하신가요"에 "예"라고 답했다면, 피로 회복 이라는 건강 목적을 추천할 수 있습니다.

어떤 이유로 어느 영양소, 어느 건강 목적을 추천했는지 이유를 작성하세요.
예를 들어, "주로 실내에서 활동하신다고 알고있습니다. 따라서 비타민 D를 추천합니다."
"요즘 잠을 잘 못 이루시나요? 피로 회복에 도움이 되는 영양제를 찾아드릴 수 있습니다."

# 사전 설문조사 내용은 다음과 같습니다:
**사전 설문 조사**: {state['user_health_info']}

# 영양소 예시는 다음과 같습니다:
**영양소**: {', '.join(nutrient_lst)}

# 영양제 종류 예시는 다음과 같습니다:
**영양제 종류**: {', '.join(supplement_types)}

# 건강 목적 예시는 다음과 같습니다:
**건강 목적**: {', '.join(purpose_tag_lst)}

# 응답 예시는 다음과 같습니다.:
[사용자 이름]님! 어떤 영양소가 포함된 영양제를 찾고 계신지, 혹은 어떤 목적을 가지고 영양제를 찾고 있는지 말씀해 주시면 더 정확한 영양제를 추천해드릴게요!
[사전 설문 조사 내용에 따른 건강 분석]. 이러한 증상 완화에 도움이 될 수 있는 영양소들을 몇 가지 추천해 드릴게요.
1. [영양소1 이름]: [영양소1 추천 이유]
2. [영양소2 이름]: [영양소2 추천 이유]
3. [영양소3 이름]: [영양소3 추천 이유]

혹은 개선하고 싶으신 아래와 같은 건강 목적을 말씀해주시면 그 목적에 맞는 영양제를 추천해드릴게요!
1. [건강 목적1]
2. [건강 목적2]
3. [건강 목적3]

어떤 영양소가 포함된 영양제를 찾으시는지, 혹은 어떤 건강 목표를 가지고 계신지 알려주시면 [사용자 이름]님께 가장 적합한 영양제를 찾아드릴게요!
""",
            user_prompt=user_query,
            response_format_json=False
        )
        node_messages.append("is_enough_supplement_info 노드: '사용자의 입력에 영양제 상품을 검색하기 위한 조건이 부족하여 영양제 상품을 검색할 수 없었습니다.'")
        print(f"정보 부족으로 진행할 수 없습니다: {response}")
        return {
            "response": response,
            "is_enough_sup_info": False
        } 
        
    node_messages.append(f"is_enough_supplement_info 노드: '사용자의 입력에 영양제 상품을 검색하기 위한 충분한 조건이 확인되었습니다. 인식된 조건(영양소: {nutrients}, 건강목적: {purpose_tags}, 영양제유형: {supplement_types})'")
    print("영양소, 건강 목적을 추출을 완료했습니다!")
    # 변경된 상태 필드만 반환
    return {
        "extracted_info": result,
        "is_enough_sup_info": True,
        "node_messages": node_messages
    }


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

    taste_lst = [
        "오렌지", "복숭아", "베리", "망고", "체리", "딸기", "파인애플",
        "바나나", "멜론", "포도", "사과", "키위", "수박"
    ]

    form_lst = [
        "알약", "캡슐", "젤리", "분말", "젤", "캔디", "액상"
    ]

    # 시스템 프롬프트 정의
    system_prompt = f"""당신은 사용자의 영양제 관련 텍스트에서 다양한 정보를 추출하는 전문가입니다.

사용자 텍스트를 분석하여 다음 정보들을 추출해주세요:

1. **맛**: {', '.join(taste_lst)}
2. **양식**: {', '.join(form_lst)}
3. **수량**: 영양제 개수 관련 숫자만 (함유량 제외)
4. **가격**: 가격 범위나 조건 (예: "2만원 이하", "저렴한")
5. **원산지**: 국가명이나 지역명
6. **별점 선호도**: 높은 별점순을 원하는지 (true/false/null)
7. **리뷰수 선호도**: 많은 리뷰수순을 원하는지 (true/false/null)
8. **비건 선호도**: 비건 제품을 원하는지 (true/false/null)

**추출 규칙:**
- 명시적으로 언급된 항목만 추출
- 정확한 이름으로 매칭 (예: "비타민C" → "비타민 C")
- 리스트에 없는 항목은 포함하지 말것
- 불린 값: true(원함), false(명시적 거부), null(언급 없음)

**응답 형식 (JSON):**
{{
  "flavors": ["항목1", "항목2"],
  "forms": ["항목1", "항목2"],
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

    # 변경된 상태 필드만 반환
    return {
        "extracted_info": result,
    } 