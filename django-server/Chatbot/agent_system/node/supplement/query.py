from typing import Dict, Any, List
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from datetime import datetime, date
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate

from ...state import AgentState
from ..base import get_llm_response
from Chatbot.models import NutritionDailyRec
from Mypage.models import UserNutrientIntake
from Account.models import CustomUser

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
    is_personalized = state.get("is_personalized", False)
    personalized_info = state.get("personalized_info", {})
    user_id = state.get("user_id")
    user_health_info = state.get("user_health_info")
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

        print("\n=== 일반 검색 완료 ===")
        print(f"최종 검색 결과 수: {len(all_results)}개")
    else:
        print("\n=== 맞춤형 영양제 검색 시작 ===")
        
        if not user_id:
            print("사용자 ID가 없습니다.")
            return {"kag_results": []}
            
        try:
            user = CustomUser.objects.get(id=user_id)
            print(f"사용자 정보: {user.email}, 성별: {user.gender}, 생년월일: {user.birth_date}")
            
            if user.gender is not None:
                if user.gender == "male":
                    gender = "남자"
                else:
                    gender = "여자"
            else:
                gender = "남자"

            # 사용자 나이 계산
            today = date.today()
            if user.birth_date is not None:
                today = date.today()
                age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))
            else:
                age = 20
            print(f"사용자 나이: {age}")
            
            # 나이대 계산 (예: 6~8, 9~11 등)
            age_range = None
            for rec in NutritionDailyRec.objects.values('age_range').distinct():
                range_str = rec['age_range']
                if '~' in range_str:
                    start, end = map(int, range_str.split('~'))
                    if start <= age <= end:
                        age_range = range_str
                        break
            
            if not age_range:
                if user_health_info["age"]:
                    if user_health_info["age"] == "19-29세":
                        age_range = "19~29"
                    elif user_health_info["age"] == "30-49세":
                        age_range = "30~49"
                    elif user_health_info["age"] == "50-64세":
                        age_range = "50~64"
                    elif user_health_info["age"] == "65세 이상":
                        age_range = "65~74"
                else:
                    age_range = "19~29"
            
            print(f"사용자 나이대: {age_range}")
            
            # 맞춤형 검색 정보를 저장할 딕셔너리
            personalized_info = {
                "user_age": age,
                "user_gender": gender,
                "age_range": age_range,
                "nutrient_analysis": []
            }

            # purpose_tag별 처리
            if extracted_info.get("purpose_tag"):
                # 우선순위 영양소 리스트
                priority_nutrients = extracted_info.get("nutrients", [])
                for tag in extracted_info["purpose_tag"]:
                    print(f"\n=== {tag} 목적 태그 처리 중 ===")
                    # 1. 해당 태그와 연결된 영양소 찾기
                    nutrient_query = f"""
                    MATCH (t:Tag {{name: '{tag}'}})<-[:HAS_TAG]-(n:Nutrient)
                    RETURN n.name as name
                    """
                    print(f"목적 태그에 해당하는 영양소 검색 쿼리:\n{nutrient_query}")
                    nutrients = execute_query(nutrient_query)
                    print(f"해당 태그와 연결된 영양소 수: {len(nutrients)}개")

                    # 우선순위 영양소 먼저, 그 다음 나머지
                    nutrient_names = [n["name"] for n in nutrients]
                    ordered_nutrients = []
                    if priority_nutrients:
                        # 우선순위 영양소만 먼저
                        ordered_nutrients += [n for n in priority_nutrients if n in nutrient_names]
                        # 나머지 영양소
                        ordered_nutrients += [n for n in nutrient_names if n not in priority_nutrients]
                    else:
                        ordered_nutrients = nutrient_names

                    for nutrient in ordered_nutrients:
                        print(f"\n=== {nutrient} (목적: {tag}) 영양소 처리 중 ===")
                        # 1. 사용자의 영양소 섭취량 확인
                        recent_intake = UserNutrientIntake.objects.filter(
                            user_id=user_id,
                            nutrient__name=nutrient,
                        ).aggregate(total=Sum('amount'))['total'] or 0
                        print(f"{nutrient} 섭취량: {recent_intake}")
                        # 2. 1일 권장 섭취량 확인
                        daily_rec = NutritionDailyRec.objects.filter(
                            sex=gender,
                            age_range=age_range,
                            nutrient=nutrient
                        ).first()
                        if not daily_rec:
                            print(f"{nutrient}의 1일 권장 섭취량 정보가 없습니다.")
                            continue
                        daily_amount = daily_rec.daily
                        print(f"{nutrient} 1일 권장 섭취량: {daily_amount}")
                        # 3. 섭취량과 권장량 비교
                        if recent_intake < daily_amount:
                            deficiency = daily_amount - recent_intake
                            deficiency_percentage = (deficiency / daily_amount) * 100
                            print(f"{nutrient} 부족량: {deficiency} ({deficiency_percentage:.1f}%)")
                            personalized_info["nutrient_analysis"].append({
                                "nutrient": nutrient,
                                "current_intake": recent_intake,
                                "daily_recommended": daily_amount,
                                "deficiency": deficiency,
                                "deficiency_percentage": round(deficiency_percentage, 1),
                                "status": "deficient",
                                "recommendation_type": "direct"
                            })
                            query = f"""
                            MATCH (s:Supplement)-[c:CONTAINS]->(n:Nutrient {{name: '{nutrient}'}})
                            RETURN s.id
                            ORDER BY c.amount ASC
                            LIMIT 20
                            """
                            print(f"생성된 쿼리:\n{query}")
                            results = execute_query(query)
                            print(f"검색 결과 수: {len(results)}개")
                            # 중복 제거하면서 추가
                            existing_ids = {r["id"] for r in all_results}
                            new_results = [r for r in results if r["id"] not in existing_ids]
                            all_results.extend(new_results)
                            # 20개가 모이면 중단
                            if len(all_results) >= 20:
                                print("20개 결과가 모여 검색을 중단합니다.")
                                break
                        else:
                            print(f"{nutrient}는 부족하지 않습니다. 같은 목적의 다른 영양소를 찾습니다.")
                        if len(all_results) >= 20:
                            break
                    if len(all_results) >= 20:
                        break

            # 영양소별 처리
            if extracted_info.get("nutrients"):
                for nutrient in extracted_info["nutrients"]:
                    print(f"\n=== {nutrient} 영양소 처리 중 ===")
                    
                    # 1. 사용자의 영양소 섭취량 확인
                    recent_intake = UserNutrientIntake.objects.filter(
                        user_id=user_id,
                        nutrient__name=nutrient,
                    ).aggregate(total=Sum('amount'))['total'] or 0
                    
                    print(f"{nutrient} 섭취량: {recent_intake}")
                    
                    # 2. 1일 권장 섭취량 확인
                    daily_rec = NutritionDailyRec.objects.filter(
                        sex=gender,
                        age_range=age_range,
                        nutrient=nutrient
                    ).first()
                    
                    if not daily_rec:
                        print(f"{nutrient}의 1일 권장 섭취량 정보가 없습니다.")
                        continue
                        
                    daily_amount = daily_rec.daily
                    print(f"{nutrient} 1일 권장 섭취량: {daily_amount}")
                    
                    # 3. 섭취량과 권장량 비교
                    if recent_intake < daily_amount:
                        # 부족한 경우 해당 영양소를 포함한 영양제 검색
                        deficiency = daily_amount - recent_intake
                        deficiency_percentage = (deficiency / daily_amount) * 100
                        print(f"{nutrient} 부족량: {deficiency} ({deficiency_percentage:.1f}%)")
                        
                        # 영양소 분석 정보 저장
                        personalized_info["nutrient_analysis"].append({
                            "nutrient": nutrient,
                            "current_intake": recent_intake,
                            "daily_recommended": daily_amount,
                            "deficiency": deficiency,
                            "deficiency_percentage": round(deficiency_percentage, 1),
                            "status": "deficient",
                            "recommendation_type": "direct"
                        })
                        
                        query = f"""
                        MATCH (s:Supplement)-[c:CONTAINS]->(n:Nutrient {{name: '{nutrient}'}})
                        RETURN s.id
                        ORDER BY c.amount ASC
                        LIMIT 20
                        """
                        
                        print(f"생성된 쿼리:\n{query}")
                        results = execute_query(query)
                        print(f"검색 결과 수: {len(results)}개")
                        
                        # 중복 제거하면서 추가
                        existing_ids = {r["id"] for r in all_results}
                        new_results = [r for r in results if r["id"] not in existing_ids]
                        all_results.extend(new_results)
                        
                    else:
                        # 과다 섭취인 경우 관련 영양소 검색
                        excess_percentage = ((recent_intake - daily_amount) / daily_amount) * 100
                        print(f"{nutrient} 과다 섭취 중 ({excess_percentage:.1f}% 초과). 관련 영양소 검색")
                        
                        # 영양소 분석 정보 저장
                        personalized_info["nutrient_analysis"].append({
                            "nutrient": nutrient,
                            "current_intake": recent_intake,
                            "daily_recommended": daily_amount,
                            "excess": recent_intake - daily_amount,
                            "excess_percentage": round(excess_percentage, 1),
                            "status": "excess",
                            "recommendation_type": "related"
                        })
                        
                        # 1. 관련 영양소 찾기
                        related_nutrients_query = f"""
                        MATCH (n1:Nutrient {{name: '{nutrient}'}})-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(n2:Nutrient)
                        WHERE n1 <> n2
                        WITH n2, count(t) as common_tags
                        ORDER BY common_tags DESC
                        LIMIT 2
                        RETURN n2.name as name, common_tags
                        """
                        
                        print(f"관련 영양소 검색 쿼리:\n{related_nutrients_query}")
                        related_nutrients = execute_query(related_nutrients_query)
                        print(f"관련 영양소 수: {len(related_nutrients)}개")
                        
                        # 2. 각 관련 영양소의 섭취량과 권장량 비교
                        for related in related_nutrients:
                            related_nutrient = related["name"]
                            print(f"\n=== {related_nutrient} 영양소 처리 중 ===")
                            
                            # 관련 영양소의 섭취량 확인
                            related_intake = UserNutrientIntake.objects.filter(
                                user_id=user_id,
                                nutrient__name=related_nutrient
                            ).aggregate(total=Sum('amount'))['total'] or 0
                            
                            print(f"{related_nutrient} 섭취량: {related_intake}")
                            
                            # 관련 영양소의 1일 권장 섭취량 확인
                            related_daily_rec = NutritionDailyRec.objects.filter(
                                sex=gender,
                                age_range=age_range, 
                                nutrient=related_nutrient
                            ).first()
                            
                            if not related_daily_rec:
                                print(f"{related_nutrient}의 1일 권장 섭취량 정보가 없습니다.")
                                continue
                                
                            related_daily_amount = related_daily_rec.daily
                            print(f"{related_nutrient} 1일 권장 섭취량: {related_daily_amount}")
                            
                            # 관련 영양소가 부족한 경우에만 영양제 추천
                            if related_intake < related_daily_amount:
                                deficiency = related_daily_amount - related_intake
                                deficiency_percentage = (deficiency / related_daily_amount) * 100
                                print(f"{related_nutrient} 부족량: {deficiency} ({deficiency_percentage:.1f}%)")
                                
                                # 관련 영양소 분석 정보 저장
                                personalized_info["nutrient_analysis"].append({
                                    "nutrient": related_nutrient,
                                    "current_intake": related_intake,
                                    "daily_recommended": related_daily_amount,
                                    "deficiency": deficiency,
                                    "deficiency_percentage": round(deficiency_percentage, 1),
                                    "status": "deficient",
                                    "recommendation_type": "related",
                                    "related_to": nutrient
                                })
                                
                                query = f"""
                                MATCH (s:Supplement)-[c:CONTAINS]->(n:Nutrient {{name: '{related_nutrient}'}})
                                RETURN s.id
                                ORDER BY c.amount ASC
                                LIMIT 20
                                """
                                
                                print(f"생성된 쿼리:\n{query}")
                                results = execute_query(query)
                                print(f"검색 결과 수: {len(results)}개")
                                
                                # 중복 제거하면서 추가
                                existing_ids = {r["id"] for r in all_results}
                                new_results = [r for r in results if r["id"] not in existing_ids]
                                all_results.extend(new_results)
                            else:
                                print(f"{related_nutrient}도 과다 섭취 중입니다. 다른 영양소를 찾습니다.")
            
            # 영양제 유형별 처리.
            # supplement_types별 처리
            if extracted_info.get("supplement_types"):
                for nutrient in extracted_info["supplement_types"]:
                    print(f"\n=== {nutrient} 영양소 처리 중 ===")
                    
                    # 1. 사용자의 영양소 섭취량 확인
                    recent_intake = UserNutrientIntake.objects.filter(
                        user_id=user_id,
                        nutrient__name=nutrient,
                    ).aggregate(total=Sum('amount'))['total'] or 0
                    
                    print(f"{nutrient} 섭취량: {recent_intake}")
                    
                    # 2. 1일 권장 섭취량 확인
                    daily_rec = NutritionDailyRec.objects.filter(
                        sex=gender,
                        age_range=age_range,
                        nutrient=nutrient
                    ).first()
                    
                    if not daily_rec:
                        print(f"{nutrient}의 1일 권장 섭취량 정보가 없습니다.")
                        continue
                        
                    daily_amount = daily_rec.daily
                    print(f"{nutrient} 1일 권장 섭취량: {daily_amount}")
                    
                    # 3. 섭취량과 권장량 비교
                    if recent_intake < daily_amount:
                        # 부족한 경우 해당 영양소를 포함한 영양제 검색
                        deficiency = daily_amount - recent_intake
                        deficiency_percentage = (deficiency / daily_amount) * 100
                        print(f"{nutrient} 부족량: {deficiency} ({deficiency_percentage:.1f}%)")
                        
                        # 영양소 분석 정보 저장
                        personalized_info["nutrient_analysis"].append({
                            "nutrient": nutrient,
                            "current_intake": recent_intake,
                            "daily_recommended": daily_amount,
                            "deficiency": deficiency,
                            "deficiency_percentage": round(deficiency_percentage, 1),
                            "status": "deficient",
                            "recommendation_type": "direct"
                        })
                        
                        query = f"""
                        MATCH (s:Supplement)-[c:CONTAINS]->(n:Nutrient {{name: '{nutrient}'}})
                        RETURN s.id
                        ORDER BY c.amount ASC
                        LIMIT 20
                        """
                        
                        print(f"생성된 쿼리:\n{query}")
                        results = execute_query(query)
                        print(f"검색 결과 수: {len(results)}개")
                        
                        # 중복 제거하면서 추가
                        existing_ids = {r["id"] for r in all_results}
                        new_results = [r for r in results if r["id"] not in existing_ids]
                        all_results.extend(new_results)
                        
                    else:
                        # 과다 섭취인 경우 관련 영양소 검색
                        excess_percentage = ((recent_intake - daily_amount) / daily_amount) * 100
                        print(f"{nutrient} 과다 섭취 중 ({excess_percentage:.1f}% 초과). 관련 영양소 검색")
                        
                        # 영양소 분석 정보 저장
                        personalized_info["nutrient_analysis"].append({
                            "nutrient": nutrient,
                            "current_intake": recent_intake,
                            "daily_recommended": daily_amount,
                            "excess": recent_intake - daily_amount,
                            "excess_percentage": round(excess_percentage, 1),
                            "status": "excess",
                            "recommendation_type": "related"
                        })
                        
                        # 1. 관련 영양소 찾기
                        related_nutrients_query = f"""
                        MATCH (n1:Nutrient {{name: '{nutrient}'}})-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(n2:Nutrient)
                        WHERE n1 <> n2
                        WITH n2, count(t) as common_tags
                        ORDER BY common_tags DESC
                        LIMIT 2
                        RETURN n2.name as name, common_tags
                        """
                        
                        print(f"관련 영양소 검색 쿼리:\n{related_nutrients_query}")
                        related_nutrients = execute_query(related_nutrients_query)
                        print(f"관련 영양소 수: {len(related_nutrients)}개")
                        
                        # 2. 각 관련 영양소의 섭취량과 권장량 비교
                        for related in related_nutrients:
                            related_nutrient = related["name"]
                            print(f"\n=== {related_nutrient} 영양소 처리 중 ===")
                            
                            # 관련 영양소의 섭취량 확인
                            related_intake = UserNutrientIntake.objects.filter(
                                user_id=user_id,
                                nutrient__name=related_nutrient
                            ).aggregate(total=Sum('amount'))['total'] or 0
                            
                            print(f"{related_nutrient} 섭취량: {related_intake}")
                            
                            # 관련 영양소의 1일 권장 섭취량 확인
                            related_daily_rec = NutritionDailyRec.objects.filter(
                                sex=gender,
                                age_range=age_range, 
                                nutrient=related_nutrient
                            ).first()
                            
                            if not related_daily_rec:
                                print(f"{related_nutrient}의 1일 권장 섭취량 정보가 없습니다.")
                                continue
                                
                            related_daily_amount = related_daily_rec.daily
                            print(f"{related_nutrient} 1일 권장 섭취량: {related_daily_amount}")
                            
                            # 관련 영양소가 부족한 경우에만 영양제 추천
                            if related_intake < related_daily_amount:
                                deficiency = related_daily_amount - related_intake
                                deficiency_percentage = (deficiency / related_daily_amount) * 100
                                print(f"{related_nutrient} 부족량: {deficiency} ({deficiency_percentage:.1f}%)")
                                
                                # 관련 영양소 분석 정보 저장
                                personalized_info["nutrient_analysis"].append({
                                    "nutrient": related_nutrient,
                                    "current_intake": related_intake,
                                    "daily_recommended": related_daily_amount,
                                    "deficiency": deficiency,
                                    "deficiency_percentage": round(deficiency_percentage, 1),
                                    "status": "deficient",
                                    "recommendation_type": "related",
                                    "related_to": nutrient
                                })
                                
                                query = f"""
                                MATCH (s:Supplement)-[c:CONTAINS]->(n:Nutrient {{name: '{related_nutrient}'}})
                                RETURN s.id
                                ORDER BY c.amount ASC
                                LIMIT 20
                                """
                                
                                print(f"생성된 쿼리:\n{query}")
                                results = execute_query(query)
                                print(f"검색 결과 수: {len(results)}개")
                                
                                # 중복 제거하면서 추가
                                existing_ids = {r["id"] for r in all_results}
                                new_results = [r for r in results if r["id"] not in existing_ids]
                                all_results.extend(new_results)
                            else:
                                print(f"{related_nutrient}도 과다 섭취 중입니다. 다른 영양소를 찾습니다.")
            
            print("\n=== 맞춤형 검색 완료 ===")
            print(f"최종 검색 결과 수: {len(all_results)}개")
            print(f"개인화 정보: {personalized_info}")
            
        except CustomUser.DoesNotExist:
            print("사용자를 찾을 수 없습니다.")
            return {"kag_results": []}
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            return {"kag_results": []}
    
    return {"kag_results": all_results[:20], "personalized_info": personalized_info}

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
    
    with driver.session() as session:
        query_results = session.run(query)
        for record in query_results:
            result_dict = {}
            for key in record.keys():
                result_dict[key.replace("s.", "")] = record[key]
            results.append(result_dict)

    driver.close()

    return results
