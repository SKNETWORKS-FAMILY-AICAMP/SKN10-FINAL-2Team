from typing import Dict, Any, List
import json

from ...state import AgentState, ExtractedInfo
from ..base import get_llm_json_response

def extract_nutrient_info(state: AgentState) -> Dict[str, Any]:
    """
    사용자 입력에서 영양소 관련 정보를 추출하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    # 가장 최근 사용자 메시지 추출
    messages = state.get("messages", [])
    if not messages:
        return {"needs_human_input": True, "human_input_request": "영양소에 대해 더 자세히 알려주세요."}
    
    latest_message = messages[-1]
    if latest_message.type != "human":
        return {"needs_human_input": True, "human_input_request": "영양소에 대해 더 자세히 알려주세요."}
    
    user_query = latest_message.content
    
    # 영양소 리스트 정의
    nutrient_lst = [
        "비타민 A", "베타카로틴", "비타민 D", "비타민 E", "비타민 K", "비타민 B1", "비타민 B2",
        "나이아신", "판토텐산", "비타민 B6", "엽산", "비타민 B12", "비오틴", "비타민 C", "칼슘", "마그네슘",
        "철", "아연", "구리", "셀레늄", "요오드", "망간", "몰리브덴", "칼륨", "크롬", "루테인", "인",
        "메티오닌", "시스테인", "류신", "트립토판", "라이신", "트레오닌", "페닐알라닌", "티로신", "오메가3"
    ]
    
    # 시스템 프롬프트 정의
    system_prompt = f"""당신은 사용자의 메시지에서 영양소 관련 정보를 추출하는 전문가입니다.

다음 영양소 목록 중에서 사용자가 언급한 영양소를 추출해주세요:
{', '.join(nutrient_lst)}

또한 사용자가 영양소에 대해 어떤 정보를 알고 싶어하는지 의도를 파악해주세요.
가능한 의도 카테고리:
- "효능": 영양소의 효능이나 이점
- "상호작용": 다른 영양소나 약물과의 상호작용
- "섭취방법": 올바른 섭취 방법이나 시간
- "부작용": 과다 섭취 시 부작용이나 위험성
- "식품원": 해당 영양소가 풍부한 식품
- "결핍증상": 해당 영양소 부족 시 나타나는 증상
- "일일권장량": 권장 섭취량
- "기타": 위 카테고리에 해당하지 않는 경우

JSON 형식으로 다음 정보를 반환해주세요:
{{
  "nutrients": ["영양소1", "영양소2", ...],
  "intent": "효능" | "상호작용" | "섭취방법" | "부작용" | "식품원" | "결핍증상" | "일일권장량" | "기타",
  "specific_question": "사용자의 구체적인 질문 요약",
  "has_sufficient_info": true | false (추출된 정보가 충분한지 여부)
}}"""

    # LLM에 요청하여 영양소 정보 추출
    result = get_llm_json_response(
        system_prompt=system_prompt,
        user_prompt=user_query
    )
    
    nutrients = result.get("nutrients", [])
    intent = result.get("intent", "기타")
    has_sufficient_info = result.get("has_sufficient_info", False)
    
    # 추출된 정보가 충분하지 않은 경우 사용자에게 추가 정보 요청
    if not nutrients or not has_sufficient_info:
        request_message = "어떤 영양소에 대해 알고 싶으신가요? 더 자세히 알려주세요."
        return {
            "needs_human_input": True,
            "human_input_request": request_message
        }
    
    # 현재 추출된 정보 가져오기 또는 초기화
    current_extracted_info = state.get("extracted_info", {})
    
    # 추출된 정보 업데이트
    updated_info = current_extracted_info.copy() if current_extracted_info else {}
    updated_info["nutrients"] = nutrients
    
    # 메타데이터에 의도 정보 저장
    metadata = state.get("metadata", {})
    metadata["nutrient_intent"] = intent
    metadata["specific_question"] = result.get("specific_question", "")
    
    # 변경된 상태 필드만 반환
    return {
        "extracted_info": updated_info,
        "metadata": metadata,
        "needs_human_input": False
    } 