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
        # 일반적인 질문인 경우 설문 데이터를 바탕으로 개인화된 영양소 추천
        user_health_info = state.get("user_health_info", {})
        
        # 설문 데이터를 바탕으로 추천할 영양소 결정
        recommended_nutrients = []
        
        # 실내 생활이 많으면 비타민 D 추천
        if user_health_info.get('indoor_daytime') == '예':
            recommended_nutrients.append("비타민 D")
        
        # 피로감이 있으면 비타민 B 복합체 추천
        if user_health_info.get('fatigue') == '예':
            recommended_nutrients.append("비타민 B12")
        
        # 수면의 질이 좋지 않으면 마그네슘 추천
        if user_health_info.get('sleep_well') == '아니오' or user_health_info.get('still_tired') == '예':
            recommended_nutrients.append("마그네슘")
        
        # 눈이 건조하면 루테인 추천
        if user_health_info.get('dry_eyes') == '예':
            recommended_nutrients.append("루테인")
        
        # 감기에 잘 걸리면 비타민 C 추천
        if user_health_info.get('frequent_cold') == '예':
            recommended_nutrients.append("비타민 C")
        
        # 기본 추천 (추천이 없을 경우)
        if not recommended_nutrients:
            recommended_nutrients = ["비타민 D", "비타민 C", "종합 비타민"]
        
        # 최대 3개까지만 추천
        recommended_nutrients = recommended_nutrients[:3]
        
        print(f"설문 기반 추천 영양소: {recommended_nutrients}")
        
        return {
            "nutrients": recommended_nutrients,
            "is_enough_nut_info": True
        }
    
    # 변경된 상태 필드만 반환
    return {
        "nutrients": nutrients,
        "is_enough_nut_info": True
    } 