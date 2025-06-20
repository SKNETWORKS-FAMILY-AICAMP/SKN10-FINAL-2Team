from typing import Dict, Any
import json

from ...state import AgentState
from ..base import get_llm_response

def generate_nutrient_response(state: AgentState) -> Dict[str, Any]:
    """
    영양소 정보를 바탕으로 사용자에게 응답을 생성하는 노드
    
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

    # 필요한 정보 가져오기
    nutrient_knowledge = state.get("nutrient_knowledge", {})
    
    # 추출된 영양소 정보 가져오기
    extracted_info = state.get("extracted_info", {})
    nutrients = extracted_info.get("nutrients", [])

    nutrient_lst = [
        "비타민 A", "베타카로틴", "비타민 D", "비타민 E", "비타민 K", "비타민 B1", "비타민 B2",
        "나이아신", "판토텐산", "비타민 B6", "엽산", "비타민 B12", "비오틴", "비타민 C", "칼슘", "마그네슘",
        "철", "아연", "구리", "셀레늄", "요오드", "망간", "몰리브덴", "칼륨", "크롬", "루테인", "인",
        "메티오닌", "시스테인", "류신", "트립토판", "이소류신", "라이신", "트레오닌", "페닐알라닌", "티로신"
    ]
    
    # 응답 생성을 위한 시스템 프롬프트
    system_prompt = """당신은 영양소 전문가로서 사용자의 질문에 정확하고 유용한 정보를 제공하는 "영양이" 챗봇입니다.
제공된 영양소 지식 데이터와 요약 정보를 바탕으로 사용자의 의도에 맞는 응답을 생성해주세요.

응답 작성 지침:
1. 사용자가 질문한 영양소의 정보를 중심으로 응답하세요.
2. 영양소의 효능, 권장 섭취량(반드시 mg, mcg), 결핍 증상, 과다 섭취 부작용 등 관련 정보를 포함하세요.
3. 다른 영양소와의 상호작용이 있다면 이를 언급하세요.
4. 정보는 명확하고 이해하기 쉽게 구성하세요.
5. 의학적 조언이 필요한 경우 전문가 상담을 권유하세요.
6. 응답은 친절하고 전문적인 톤으로 작성하세요.

응답 순서(마크다운으로 출력하세요):
[영양소 이름]에 대해 자세히 알려드릴게요!

[영양소에 대한 개요]

[영양소 이름]의 주요 정보
효능
[영양소 효능 1]
[영양소 효능 2]
[영양소 효능 3]

권장 섭취량
[권장 섭취량(반드시 mg, mcg 단위) 및 그에 대한 설명]

결핍 증상
[결핍 증상1 및 그에 대한 설명]
[결핍 증상2 및 그에 대한 설명]
[결핍 증상3 및 그에 대한 설명]

과다 섭취 부작용
[과다 섭취 부작용1 및 그에 대한 설명]
[과다 섭취 부작용2 및 그에 대한 설명]
[과다 섭취 부작용3 및 그에 대한 설명]

다른 성분과 상호작용
[상호작용 영양소1 및 그에 대한 설명]
[상호작용 영양소2 및 그에 대한 설명]
[상호작용 영양소3 및 그에 대한 설명]

[마무리]"""

    # 사용자 프롬프트 구성
    user_prompt = f"""사용자 질문: {user_query}
관련 영양소: {', '.join(nutrients)}

영양소 지식 데이터:
{json.dumps(nutrient_knowledge, ensure_ascii=False, indent=2)}

위 정보를 바탕으로 사용자 질문에 대한 응답을 생성해주세요."""

    # LLM에 요청하여 응답 생성
    response = get_llm_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    # 후속 질문 생성
    followup_prompt = f"""사용자와의 대화를 바탕으로 자연스러운 후속 질문을 1개만 생성해주세요.
후속 질문은 다음 중 하나를 목적으로 해야 합니다:
1. 다른 관련 영양소에 대한 정보 제공
2. 영양제 추천으로의 자연스러운 전환

사용자가 선택할 수 있는 영양소를 아래 영양소 예시 목록에서 추천하세요:
{', '.join(nutrient_lst)}


챗봇 응답:
{response}

후속 질문 예시
비타민 D 외에 다른 영양소, 예를 들어 비타민 K나 칼슘에 대해서도 궁금하신 점이 있으신가요? 필요하시다면 비타민 D 영양제를 추천해드릴 수도 있어요!"""

    followup_question = get_llm_response(
        system_prompt="자연스러운 후속 질문을 생성하는 전문가입니다.",
        user_prompt=followup_prompt
    )
    
    # 변경된 상태 필드만 반환
    return {
        "response": response,
        "followup_question": followup_question
    } 