from typing import Dict, Any, List
import json

from ...state import AgentState
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
    latest_message = messages[-1]
    
    user_query = latest_message.content
    
    # 영양소 리스트 정의
    nutrient_lst = [
        "비타민 A", "베타카로틴", "비타민 D", "비타민 E", "비타민 K", "비타민 B1", "비타민 B2",
        "나이아신", "판토텐산", "비타민 B6", "엽산", "비타민 B12", "비오틴", "비타민 C", "칼슘", "마그네슘",
        "철", "아연", "구리", "셀레늄", "요오드", "망간", "몰리브덴", "칼륨", "크롬", "루테인", "인",
        "메티오닌", "시스테인", "류신", "트립토판", "이소류신", "라이신", "트레오닌", "페닐알라닌", "티로신"
    ]
    
    # 시스템 프롬프트 정의
    system_prompt = f"""당신은 사용자의 메시지에서 영양소 관련 정보를 추출하는 전문가입니다.

다음 영양소 목록 중에서 사용자가 언급한 영양소를 추출해주세요:
{', '.join(nutrient_lst)}

JSON 형식으로 다음 정보를 반환해주세요:
{{
  "nutrients": ["영양소1", "영양소2", ...]
}}"""

    # LLM에 요청하여 영양소 정보 추출
    result = get_llm_json_response(
        system_prompt=system_prompt,
        user_prompt=user_query
    )
    
    nutrients = result.get("nutrients", [])

    if not nutrients:
        response = get_llm_json_response(
            system_prompt=f"""당신은 영양제와 영양소에 관한 전문 지식을 갖춘 친절한 챗봇입니다.
영양소, 영양제와 관련없는 질문은 대답하지 마세요.
사용자에게 어떤 영양소에 대한 정보를 얻고싶은지 네 문장으로 물어보세요.

사용자의 사전 설문조사 내용을 참고하여 어떤 영양소를 물어볼 수 있는지 영양소 예시에 있는 영양소 3가지만 추천해주세요.

예를 들면, 사전 설문조사 내용에서 주로 실내에서 활동하신다고 응답하셨는데 비타민 D에 대한 정보를 알려드릴까요? 라고 말할 수 있습니다.

사전 설문조사 내용은 다음과 같습니다:
**사전 설문 조사**: {state['user_health_info']}

영양소 예시는 다음과 같습니다:
**영양소**: {', '.join(nutrient_lst)}
""",
            user_prompt=user_query,
            response_format_json=False
        )

        print(f"정보 부족으로 진행할 수 없습니다: {response}")

        return {
            "response": response,
            "is_enough_nut_info": False
        }
    
    # 변경된 상태 필드만 반환
    return {
        "nutrients": nutrients,
        "is_enough_nut_info": True
    } 