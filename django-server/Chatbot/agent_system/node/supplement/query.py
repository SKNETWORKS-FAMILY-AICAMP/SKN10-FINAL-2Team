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
    extracted_info를 바탕으로 그래프 DB Cypher 쿼리를 직접 생성하는 함수
    """
    extracted_info = state.get("extracted_info", {})
    
    # 기본 MATCH 절 시작
    query_parts = ["MATCH (s:Supplement)"]
    where_conditions = []
    
    # 영양소 필터링
    if extracted_info.get("nutrients"):
        query_parts.append("MATCH (s)-[:CONTAINS]->(n:Nutrient)")
        nutrient_conditions = [f"n.name = '{nutrient}'" for nutrient in extracted_info["nutrients"]]
        where_conditions.append(f"({' OR '.join(nutrient_conditions)})")
    
    # 영양제 종류 필터링
    if extracted_info.get("supplement_types"):
        query_parts.append("MATCH (s)-[:BELONGS_TO]->(c:Category)")
        category_conditions = [f"c.name = '{cat}'" for cat in extracted_info["supplement_types"]]
        where_conditions.append(f"({' OR '.join(category_conditions)})")
    
    # 건강 목적 필터링
    if extracted_info.get("purpose_tag"):
        query_parts.append("MATCH (n:Nutrient)-[:HAS_TAG]->(t:Tag)")
        tag_conditions = [f"t.name = '{tag}'" for tag in extracted_info["purpose_tag"]]
        where_conditions.append(f"({' OR '.join(tag_conditions)})")
    
    # 원산지 필터링
    if extracted_info.get("origins"):
        query_parts.append("MATCH (s)-[:MADE_IN]->(co:Country)")
        origin_conditions = [f"co.name = '{origin}'" for origin in extracted_info["origins"]]
        where_conditions.append(f"({' OR '.join(origin_conditions)})")
    
    # 맛 필터링
    if extracted_info.get("flavors"):
        query_parts.append("MATCH (s)-[:HAS_FLAVOR]->(f:Flavor)")
        flavor_conditions = [f"f.name = '{flavor}'" for flavor in extracted_info["flavors"]]
        where_conditions.append(f"({' OR '.join(flavor_conditions)})")
    
    # 형태 필터링
    if extracted_info.get("forms"):
        query_parts.append("MATCH (s)-[:HAS_FORM]->(fo:Form)")
        form_conditions = [f"fo.name = '{form}'" for form in extracted_info["forms"]]
        where_conditions.append(f"({' OR '.join(form_conditions)})")
    
    # 수량 필터링
    if extracted_info.get("quantities"):
        quantity_conditions = []
        for quantity in extracted_info["quantities"]:
            try:
                # 수량에서 숫자만 추출
                qty_num = int(''.join(filter(str.isdigit, quantity)))
                quantity_conditions.append(f"(toInteger(split(s.quantity, ' ')[0]) >= {qty_num - 20} AND toInteger(split(s.quantity, ' ')[0]) <= {qty_num + 20})")
            except (ValueError, IndexError):
                continue
        if quantity_conditions:
            where_conditions.append(f"({' OR '.join(quantity_conditions)})")
    
    # 비건 여부 필터링
    if extracted_info.get("is_vegan") is not None:
        where_conditions.append(f"s.is_vegan = {str(extracted_info['is_vegan']).lower()}")
    
    # WHERE 절 추가
    if where_conditions:
        query_parts.append("WHERE " + " AND ".join(where_conditions))
    
    # ORDER BY 절 추가
    if extracted_info.get("order_ratings"):
        query_parts.append("ORDER BY s.rating DESC")
    elif extracted_info.get("order_reviewcnt"):
        query_parts.append("ORDER BY s.review_count DESC")
    else:
        query_parts.append("ORDER BY rand()")
    
    # RETURN 절 추가
    query_parts.append("RETURN s.id")
    query_parts.append("LIMIT 20")
    
    # 최종 쿼리 생성
    cypher_query = "\n".join(query_parts)
    print(f"생성된 Cypher 쿼리: {cypher_query}")
    
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
    
    # Neo4j 연결
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    results = []
    
    with driver.session() as session:
        # 쿼리 실행
        query_results = session.run(kag_query)
        
        # Record 객체를 딕셔너리로 변환
        for record in query_results:
            result_dict = {}
            for key in record.keys():
                result_dict[key.replace("s.", "")] = record[key]
            results.append(result_dict)

        driver.close()
    
    # 변경된 상태 필드만 반환
    return {"kag_results": results} 