from typing import Dict, Any, List
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

from ...state import AgentState
from ..base import get_llm_response

# 환경변수 로드
load_dotenv()

# Neo4j 연결 정보
URI = "neo4j+ssc://4d5cd572.databases.neo4j.io"
USERNAME = "neo4j"
PASSWORD = "Zx86I42iwxvqd5G2SUKdrLgDHuY62vhl037CfwnpgwY"

def execute_kag_query(state: AgentState) -> Dict[str, Any]:
    """
    extracted_info를 바탕으로 그래프 DB Cypher 쿼리를 생성하고 실행하는 노드
    결과가 20개 미만일 경우 단계적으로 필터링을 제거하며 추가 결과를 가져옵니다.
    """
    extracted_info = state.get("extracted_info", {})
    is_personalized = state.get("is_personalized", {})
    all_results = []

    if not is_personalized:
        print("\n=== 영양제 검색 시작 ===")
        print(f"초기 검색 조건: {extracted_info}")
        
        # 1단계: 모든 조건으로 쿼리 실행
        current_info = extracted_info.copy()
        query = build_query(current_info)
        print("\n=== 1단계: 모든 조건으로 검색 ===")
        print(f"생성된 쿼리:\n{query}")
        results = execute_query(query)
        print(f"검색 결과 수: {len(results)}개")
        all_results.extend(results)
        
        # 2단계: 원산지, 맛, 형태, 수량, 비건 여부 필터링 제거
        if len(all_results) < 20:
            print("\n=== 2단계: 원산지, 맛, 형태, 수량, 비건 여부 필터링 제거 ===")
            current_info.pop("origins", None)
            current_info.pop("flavors", None)
            current_info.pop("forms", None)
            current_info.pop("quantities", None)
            current_info.pop("is_vegan", None)
            print(f"수정된 검색 조건: {current_info}")
            
            query = build_query(current_info)
            print(f"생성된 쿼리:\n{query}")
            results = execute_query(query)
            print(f"검색 결과 수: {len(results)}개")
            # 중복 제거하면서 추가
            existing_ids = {r["id"] for r in all_results}
            new_results = [r for r in results if r["id"] not in existing_ids]
            print(f"중복 제거 후 추가된 결과 수: {len(new_results)}개")
            all_results.extend(new_results)
        
        # 3단계: 영양제 종류 필터링 제거
        if len(all_results) < 20:
            print("\n=== 3단계: 영양제 종류 필터링 제거 ===")
            current_info.pop("supplement_types", None)
            print(f"수정된 검색 조건: {current_info}")
            
            query = build_query(current_info)
            print(f"생성된 쿼리:\n{query}")
            results = execute_query(query)
            print(f"검색 결과 수: {len(results)}개")
            # 중복 제거하면서 추가
            existing_ids = {r["id"] for r in all_results}
            new_results = [r for r in results if r["id"] not in existing_ids]
            print(f"중복 제거 후 추가된 결과 수: {len(new_results)}개")
            all_results.extend(new_results)
        
        # 4단계: 영양소 필터링 제거
        if len(all_results) < 20:
            print("\n=== 4단계: 영양소 필터링 제거 ===")
            current_info.pop("nutrients", None)
            print(f"수정된 검색 조건: {current_info}")
            
            query = build_query(current_info)
            print(f"생성된 쿼리:\n{query}")
            results = execute_query(query)
            print(f"검색 결과 수: {len(results)}개")
            # 중복 제거하면서 추가
            existing_ids = {r["id"] for r in all_results}
            new_results = [r for r in results if r["id"] not in existing_ids]
            print(f"중복 제거 후 추가된 결과 수: {len(new_results)}개")
            all_results.extend(new_results)
    
    else:
        pass
    
    print("\n=== 검색 완료 ===")
    print(f"최종 검색 결과 수: {len(all_results)}개")
    return {"kag_results": all_results[:20]} 

def build_query(filtered_info: Dict[str, Any]) -> str:
    """주어진 정보로 Cypher 쿼리를 생성하는 내부 함수"""
    query_parts = ["MATCH (s:Supplement)"]
    where_conditions = []
    
    # 영양소 필터링
    if filtered_info.get("nutrients"):
        query_parts.append("MATCH (s)-[:CONTAINS]->(n:Nutrient)")
        nutrient_conditions = [f"n.name = '{nutrient}'" for nutrient in filtered_info["nutrients"]]
        where_conditions.append(f"({' OR '.join(nutrient_conditions)})")
    
    # 영양제 종류 필터링
    if filtered_info.get("supplement_types"):
        query_parts.append("MATCH (s)-[:BELONGS_TO]->(c:Category)")
        category_conditions = [f"c.name = '{cat}'" for cat in filtered_info["supplement_types"]]
        where_conditions.append(f"({' OR '.join(category_conditions)})")
    
    # 건강 목적 필터링
    if filtered_info.get("purpose_tag"):
        query_parts.append("MATCH (n:Nutrient)-[:HAS_TAG]->(t:Tag)")
        tag_conditions = [f"t.name = '{tag}'" for tag in filtered_info["purpose_tag"]]
        where_conditions.append(f"({' OR '.join(tag_conditions)})")
    
    # 원산지 필터링
    if filtered_info.get("origins"):
        query_parts.append("MATCH (s)-[:MADE_IN]->(co:Country)")
        origin_conditions = [f"co.name = '{origin}'" for origin in filtered_info["origins"]]
        where_conditions.append(f"({' OR '.join(origin_conditions)})")
    
    # 맛 필터링
    if filtered_info.get("flavors"):
        query_parts.append("MATCH (s)-[:HAS_FLAVOR]->(f:Flavor)")
        flavor_conditions = [f"f.name = '{flavor}'" for flavor in filtered_info["flavors"]]
        where_conditions.append(f"({' OR '.join(flavor_conditions)})")
    
    # 형태 필터링
    if filtered_info.get("forms"):
        query_parts.append("MATCH (s)-[:HAS_FORM]->(fo:Form)")
        form_conditions = [f"fo.name = '{form}'" for form in filtered_info["forms"]]
        where_conditions.append(f"({' OR '.join(form_conditions)})")
    
    # 수량 필터링
    if filtered_info.get("quantities"):
        quantity_conditions = []
        for quantity in filtered_info["quantities"]:
            try:
                qty_num = int(''.join(filter(str.isdigit, quantity)))
                quantity_conditions.append(f"(toInteger(split(s.quantity, ' ')[0]) >= {qty_num - 20} AND toInteger(split(s.quantity, ' ')[0]) <= {qty_num + 20})")
            except (ValueError, IndexError):
                continue
        if quantity_conditions:
            where_conditions.append(f"({' OR '.join(quantity_conditions)})")
    
    # 비건 여부 필터링
    if filtered_info.get("is_vegan") is not None:
        where_conditions.append(f"s.is_vegan = {str(filtered_info['is_vegan']).lower()}")
    
    # WHERE 절 추가
    if where_conditions:
        query_parts.append("WHERE " + " AND ".join(where_conditions))
    
    # ORDER BY 절 추가
    if filtered_info.get("order_ratings"):
        query_parts.append("ORDER BY s.rating DESC")
    elif filtered_info.get("order_reviewcnt"):
        query_parts.append("ORDER BY s.review_count DESC")
    else:
        query_parts.append("ORDER BY rand()")
    
    # RETURN 절 추가
    query_parts.append("RETURN s.id")
    query_parts.append("LIMIT 20")
    
    return "\n".join(query_parts)

def execute_query(query: str) -> List[Dict[str, Any]]:
    """Neo4j에 쿼리를 실행하고 결과를 반환하는 내부 함수"""
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    results = []
    
    try:
        with driver.session() as session:
            query_results = session.run(query)
            for record in query_results:
                result_dict = {}
                for key in record.keys():
                    result_dict[key.replace("s.", "")] = record[key]
                results.append(result_dict)
    finally:
        driver.close()
    
    return results
