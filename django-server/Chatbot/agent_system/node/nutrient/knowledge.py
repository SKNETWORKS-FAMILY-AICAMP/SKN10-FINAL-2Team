from typing import Dict, Any, List
import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

from ...state import AgentState
from ..base import get_llm_json_response

# 환경변수 로드
load_dotenv()

# Neo4j 연결 정보
URI = "neo4j+ssc://4d5cd572.databases.neo4j.io"
USERNAME = "neo4j"
PASSWORD = "Zx86I42iwxvqd5G2SUKdrLgDHuY62vhl037CfwnpgwY"

def search_nutrient_knowledge(state: AgentState) -> Dict[str, Any]:
    """
    영양소 관련 지식베이스 검색 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    # 추출된 영양소 정보 가져오기
    nutrients = state.get("nutrients", [])
    nutrient_knowledge = state.get("nutrient_knowledge", {})
    
    # 검색 결과 저장할 딕셔너리
    nutrient_knowledge = {
        "effects": [],      # 효능 정보
        "interactions": [], # 상호작용 정보
        "combinations": []  # 조합 정보
    }
    
    # Neo4j 연결
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    
    try:
        with driver.session() as session:
            # 1. 영양소 효능 검색
            for nutrient in nutrients:
                # 영양소 기본 정보 쿼리
                nutrient_query = """
                MATCH (n:Nutrient {name: $nutrient_name})
                RETURN n.name as name, n.efficacy as efficacy, n.side_effects as side_effects,
                       n.absorption_factors as absorption_factors, n.recommended_daily_intake as rdi,
                       n.food_sources as food_sources, n.deficiency_symptoms as deficiency_symptoms,
                       n.excess_symptoms as excess_symptoms
                """
                
                result = session.run(nutrient_query, nutrient_name=nutrient)
                nutrient_data = result.single()
                
                if nutrient_data:
                    nutrient_knowledge["effects"].append({
                        "nutrient": nutrient,
                        "efficacy": nutrient_data["efficacy"],
                        "side_effects": nutrient_data["side_effects"],
                        "absorption_factors": nutrient_data["absorption_factors"],
                        "recommended_daily_intake": nutrient_data["rdi"],
                        "food_sources": nutrient_data["food_sources"],
                        "deficiency_symptoms": nutrient_data["deficiency_symptoms"],
                        "excess_symptoms": nutrient_data["excess_symptoms"]
                    })
                
                # 2. 영양소 상호작용 검색
                interactions_query = """
                MATCH (n:Nutrient {name: $nutrient_name})-[r:SYNERGIZES_WITH]->(other:Nutrient)
                RETURN other.name as synergy_nutrient, r.effect as synergy_effect, 'synergistic' as interaction_type
                UNION
                MATCH (n:Nutrient {name: $nutrient_name})-[r:ANTAGONIZES_WITH]->(other:Nutrient)
                RETURN other.name as synergy_nutrient, r.effect as synergy_effect, 'antagonistic' as interaction_type
                """
                
                results = session.run(interactions_query, nutrient_name=nutrient)
                
                for record in results:
                    nutrient_knowledge["interactions"].append({
                        "nutrient": nutrient,
                        "interacting_nutrient": record["synergy_nutrient"],
                        "effect": record["synergy_effect"],
                        "type": record["interaction_type"]
                    })
                
                # 3. 영양소 조합 검색 (태그 기반)
                combinations_query = """
                MATCH (n:Nutrient {name: $nutrient_name})-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(other:Nutrient)
                WHERE n.name <> other.name
                RETURN other.name as related_nutrient, t.name as tag, count(t) as tag_count
                ORDER BY tag_count DESC
                LIMIT 5
                """
                
                results = session.run(combinations_query, nutrient_name=nutrient)
                
                for record in results:
                    nutrient_knowledge["combinations"].append({
                        "nutrient": nutrient,
                        "related_nutrient": record["related_nutrient"],
                        "common_tag": record["tag"],
                        "relevance_score": record["tag_count"]
                    })
    
    except Exception as e:
        print(f"Neo4j 검색 중 오류 발생: {e}")
    
    finally:
        driver.close()
    
    # 변경된 상태 필드만 반환
    return {"nutrient_knowledge": nutrient_knowledge}

# def summarize_nutrient_info(state: AgentState) -> Dict[str, Any]:
#     """
#     검색된 영양소 정보를 종합하여 요약하는 노드
    
#     Args:
#         state: 현재 에이전트 상태
        
#     Returns:
#         변경된 상태 필드만 포함하는 딕셔너리
#     """
#     knowledge = state.get("nutrient_knowledge", {})
    
#     # 영양소 정보 요약을 위한 시스템 프롬프트
#     system_prompt = """당신은 영양소 정보를 종합하여 요약하는 전문가입니다.
# 제공된 영양소 지식 데이터를 바탕으로 사용자의 의도에 맞게 정보를 요약해주세요.

# 다음 카테고리로 정보를 구성해주세요:
# 1. primary_nutrients: 사용자 질문에 가장 관련 있는 주요 영양소
# 2. synergistic_nutrients: 주요 영양소와 시너지 효과가 있는 영양소
# 3. antagonistic_nutrients: 주요 영양소와 상충 효과가 있는 영양소
# 4. recommended_forms: 권장되는 섭취 형태
# 5. usage_guidelines: 섭취 가이드라인 (시간, 방법, 주의사항 등)

# JSON 형식으로 다음 정보를 반환해주세요:
# {
#   "primary_nutrients": ["영양소1", "영양소2", ...],
#   "synergistic_nutrients": ["영양소1", "영양소2", ...],
#   "antagonistic_nutrients": ["영양소1", "영양소2", ...],
#   "recommended_forms": ["형태1", "형태2", ...],
#   "usage_guidelines": ["가이드라인1", "가이드라인2", ...]
# }"""

#     # 사용자 프롬프트 구성
#     user_prompt = f"""
# 사용자 질문: {specific_question}

# 영양소 지식 데이터:
# {json.dumps(knowledge, ensure_ascii=False, indent=2)}

# 위 정보를 바탕으로 사용자 의도에 맞게 영양소 정보를 요약해주세요."""

#     # LLM에 요청하여 영양소 정보 요약
#     result = get_llm_json_response(
#         system_prompt=system_prompt,
#         user_prompt=user_prompt
#     )
    
#     # 변경된 상태 필드만 반환
#     return {"nutrient_summary": result} 