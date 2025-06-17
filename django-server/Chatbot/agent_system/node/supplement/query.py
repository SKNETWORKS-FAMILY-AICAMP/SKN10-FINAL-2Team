from typing import Dict, Any, List
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

from ...state import AgentState
from ..base import get_llm_response

import re
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_openai import ChatOpenAI

# 환경변수 로드
load_dotenv()

# Neo4j 연결 정보
URI = "neo4j+ssc://4d5cd572.databases.neo4j.io"
USERNAME = "neo4j"
PASSWORD = "Zx86I42iwxvqd5G2SUKdrLgDHuY62vhl037CfwnpgwY"

def build_kag_query(state: AgentState) -> Dict[str, Any]:
    """
    extracted_info를 바탕으로 그래프 DB Cypher 쿼리를 생성하는 Agent
    LangChain의 GraphCypherQAChain을 사용하여 Neo4j 그래프 DB 구조를 자동으로 추출하고 LLM에게 제공
    """
    extracted_info = state.get("extracted_info", {})

    # Neo4j 연결 설정
    uri = "neo4j+ssc://4d5cd572.databases.neo4j.io"
    username = "neo4j"
    password = "Zx86I42iwxvqd5G2SUKdrLgDHuY62vhl037CfwnpgwY"
    
    # Neo4j 그래프 객체 생성 (최신 버전)
    try:
        graph = Neo4jGraph(
            url=uri,
            username=username,
            password=password
        )
        
        # 스키마 정보 출력
        print("Neo4j 스키마 정보 추출 중...")
        schema_info = graph.get_schema
        print(f"Neo4j 스키마: {schema_info}")
    except Exception as e:
        print(f"Neo4j 연결 오류: {str(e)}")
        # 기본 쿼리 반환
        return {"kag_query": "MATCH (s:Supplement) RETURN s.id LIMIT 20"}
    
    # LLM 설정 (OpenAI API 키 사용)
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # GraphCypherQAChain 생성 (최신 버전)
    try:
        chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            return_intermediate_steps=True,
            allow_dangerous_requests=True  # 필수 파라미터 추가
        )
    except Exception as e:
        print(f"GraphCypherQAChain 생성 오류: {str(e)}")
        # 기본 쿼리 반환
        return {"kag_query": "MATCH (s:Supplement) RETURN s.id LIMIT 20"}
    
    # 사용자 요구사항을 텍스트로 변환
    requirements = []

    if extracted_info.get("nutrients"):
        requirements.append(f"영양소: {', '.join(extracted_info['nutrients'])}")

    if extracted_info.get("supplement_types"):
        requirements.append(f"영양제 종류: {', '.join(extracted_info['supplement_types'])}")

    if extracted_info.get("purpose_tag"):
        requirements.append(f"건강 목적: {', '.join(extracted_info['purpose_tag'])}")

    if extracted_info.get("origins"):
        requirements.append(f"원산지: {', '.join(extracted_info['origins'])}")

    if extracted_info.get("flavors"):
        requirements.append(f"맛: {', '.join(extracted_info['flavors'])}")

    if extracted_info.get("forms"):
        requirements.append(f"형태: {', '.join(extracted_info['forms'])}")

    if extracted_info.get("quantities"):
        requirements.append(f"수량: {', '.join(extracted_info['quantities'])}")

    if extracted_info.get("is_vegan") is not None:
        vegan_text = "비건 제품" if extracted_info["is_vegan"] else "비건이 아닌 제품"
        requirements.append(f"비건 여부: {vegan_text}")

    if extracted_info.get("order_ratings"):
        requirements.append("높은 별점 우선")

    if extracted_info.get("order_reviewcnt"):
        requirements.append("많은 리뷰수 우선")

    # 사용자 요구사항 텍스트 생성
    user_requirements = "사용자 요구사항:\n" + "\n".join(f"- {req}" for req in requirements)
    print(user_requirements)
    # 쿼리 생성을 위한 질문 구성
    query_question = f"""
다음 사용자 요구사항에 맞는 Cypher 쿼리를 생성해주세요:

{user_requirements}

쿼리 생성 규칙:
1. MATCH 절에서 필요한 노드와 관계를 정의 (MATCH (s:Supplement) 필수)
2. MATCH 절에서 반드시 아래 명시되어 있는 필터링 조건만 적용(여러 조건이 있을경우 모두 적용)
 - 영양소(nutrients) 필터링: (s:Supplement)-[:CONTAINS]->(:Nutrient {{name: 영양소}})
 - 영양제 종류(Category) 필터링: (s:Supplement)-[:BELONGS_TO]->(:Category {{name: 영양제 종류}})
 - 건강 목적(purpose_tag) 필터링: (n:Nutrient)-[:HAS_TAG]->(:Tag {{name: 건강 목적}})
 - 원산지(Country) 필터링: (s:Supplement)-[:MADE_IN]->(:Country {{name: 원산지}})
 - 맛(flavors) 필터링: (s:Supplement)-[:HAS_FLAVOR]->(:Flavor {{name: 맛}})
 - 형태(forms) 필터링: (s:Supplement)-[:HAS_FORM]->(:Form {{name: 형태}})
 - 수량(quantities) 필터링: s.quantity = 해당 수량에서 +20 또는 -20 범위 내에 있는 상품
 - 비건 여부(is_vegan) 필터링: s.vegan = true/false
3. ORDER BY 절에서 우선순위 정렬(사용자가 직접적으로 요구할 경우만)
 - 높은 별점 우선: ORDER BY s.rating DESC
 - 많은 리뷰수 우선: ORDER BY s.review_count DESC
 - 랜덤 샘플링: 사용자가 특별한 정렬 순서를 요구하지 않았거나, 20개 이상의 결과에서 랜덤으로 선택하려면 ORDER BY rand()를 사용
4. LIMIT 20으로 결과 수 제한
5. RETURN 절에서 Supplement 노드의 id 속성(s.id)만 반환

주의사항:
- 속성 이름을 정확히 사용하세요
- 실제 데이터 구조에 없는 관계나 속성을 사용하지 마세요.
- 사용자가 특정 정렬 기준을 명시하지 않은 경우, ORDER BY rand()를 사용하여 랜덤 샘플링을 적용하세요

순수한 Cypher 쿼리문만 반환하세요. 설명이나 추가 텍스트 없이 쿼리만 작성해주세요.
"""

    try:
        # GraphCypherQAChain을 사용하여 쿼리 생성
        result = chain.invoke({"query": query_question})
        print(f"GraphCypherQAChain 결과: {result}")
        
        # 중간 단계에서 생성된 Cypher 쿼리 추출
        if 'intermediate_steps' in result and len(result['intermediate_steps']) >= 1:
            # 최신 버전에서는 첫 번째 중간 단계에서 'query' 키로 Cypher 쿼리를 제공
            cypher_query = result['intermediate_steps'][0]['query']
            print(f"중간 단계에서 추출한 쿼리: {cypher_query}")
        else:
            # 중간 단계가 없는 경우 최종 결과에서 쿼리 추출 시도
            cypher_query = result.get('result', '')
            print(f"결과에서 추출한 텍스트: {cypher_query}")
            
            # 결과에서 Cypher 쿼리 부분만 추출 (마크다운 코드 블록 제거)
            cypher_match = re.search(r'```(?:cypher|sql)?\s*(.*?)```', cypher_query, re.DOTALL)
            if cypher_match:
                cypher_query = cypher_match.group(1).strip()
                print(f"마크다운에서 추출한 쿼리: {cypher_query}")
            else:
                # 마크다운 코드 블록이 없는 경우 전체 텍스트 사용
                cypher_query = result.get('result', '').strip()
                print("마크다운이 없어 전체 텍스트를 사용합니다")
        
        # 쿼리 정리 (코드 블록 마크다운 제거)
        cypher_query = cypher_query.replace('```cypher', '').replace('```sql', '').replace('```', '').replace('`', '').strip()
        
        print(f"최종 Cypher 쿼리: {cypher_query}")
        
    except Exception as e:
        print(f"GraphCypherQAChain 오류: {str(e)}")
        
        # 오류 발생 시 기본 쿼리 생성
        cypher_query = """
        MATCH (s:Supplement)
        RETURN s.id
        LIMIT 20
        """
        print(f"기본 쿼리 사용: {cypher_query}")

    # 변경된 상태 필드만 반환
    return {"kag_query": cypher_query}

def execute_kag_query(state: AgentState) -> Dict[str, Any]:
    """
    생성된 Cypher 쿼리를 Neo4j에 실행하는 노드
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """
    # 쿼리 가져오기
    kag_query = state.get("kag_query", "")
    
    if not kag_query:
        # 기본 쿼리 설정
        kag_query = """
        MATCH (s:Supplement)
        RETURN s.id, s.name, s.rating, s.quantity, s.review_count, s.is_vegan, s.total_price
        ORDER BY rand()
        LIMIT 20
        """
    
    # Neo4j 연결
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    results = []
    
    try:
        with driver.session() as session:
            # 쿼리 실행
            query_results = session.run(kag_query)
            
            # Record 객체를 딕셔너리로 변환
            for record in query_results:
                result_dict = {}
                for key in record.keys():
                    result_dict[key.replace("s.", "")] = record[key]
                results.append(result_dict)
    
    except Exception as e:
        print(f"Neo4j 쿼리 실행 중 오류 발생: {e}")
    
    finally:
        driver.close()
    
    # 변경된 상태 필드만 반환
    return {"kag_results": results} 