# --------------------------
# 1. 상태 정의 (Blackboard 구조)
# --------------------------
from typing import Dict, Any, List, TypedDict, Optional
from openai import OpenAI
import json
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

class AgentState(TypedDict):
    user_query: str
    user_health_info: Dict[str, any]
    extracted_info: Dict[str, any]
    kag_query: str
    kag_results: List[any]
    rerank_results: List[any]
    final_results: List[any]
    final_recommendation: str
    product_ids: List[Dict[str, Any]]


# --------------------------
# 2. extract_health_info
# --------------------------
def extract_health_info(state: AgentState) -> Dict[str, Any]:
    """
    사용자 입력에서 건강 정보를 추출하여 기존 설문조사 데이터를 업데이트하는 함수

    Args:
        state: 현재 에이전트 상태
        - user_query: 사용자 입력
        - user_health_info: 기존 건강 정보 (설문조사 데이터)

    Returns:
        변경된 상태 필드만 포함하는 딕셔너리
    """

    user_query = state["user_query"]
    current_health_data = state.get("user_health_info")

    # 개선된 system_prompt
    system_prompt = f"""당신은 건강 정보 추출 전문가입니다.

**임무**: 사용자의 입력에서 건강 관련 정보를 추출하여 기존 설문조사 데이터를 업데이트하세요.

**현재 설문조사 데이터**:
```json
{json.dumps(current_health_data, ensure_ascii=False, indent=2)}
```

**지침**:
1. 사용자 입력에서 설문조사 항목과 관련된 정보만 추출하세요.
2. 기존 데이터를 수정하거나 새로운 정보를 추가하세요.
3. 확실하지 않은 정보는 추가하지 마세요.
4. 알레르기 정보는 리스트에 추가하세요 (기존 항목 유지).
5. 약물 정보도 리스트에 추가하세요 (기존 항목 유지).

**응답 형식**:
다음과 같은 JSON 형태로 응답하세요:
{{
  "updated_health_info": {{업데이트된 전체 건강 정보}},
  "extracted_changes": {{
    "category": "변경된 카테고리",
    "field": "변경된 필드명",
    "old_value": "기존 값",
    "new_value": "새로운 값",
    "action": "add|update|remove"
  }}
}}

**예시**:
- "대두 알레르기가 있어" → 알레르기 목록에 "대두" 추가
- "요즘 운동을 시작했어" → "규칙적으로 운동을 하시나요?" 값을 "예"로 변경
- "담배를 끊었어" → "담배를 피우시나요?" 값을 "아니오"로 변경"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}  # JSON 응답 강제
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    # 상태 변경사항만 반환 (LangGraph가 자동으로 적용)
    return {"user_health_info": result.get("updated_health_info", current_health_data)}


# --------------------------
# 3. extract_comprehensive_info
# --------------------------
def extract_comprehensive_info(state: AgentState) -> Dict[str, Any]:
    """
    사용자 쿼리에서 영양소, 맛, 영양제 종류, 수량, 양식, 평점, 리뷰 수, 가격, 원산지, 비건 여부를 한 번에 추출
    """

    query = state["user_query"]

    # 추출할 정보를 담을 딕셔너리 초기화
    extracted_info = {
        "nutrients": [],          # 직접 언급된 영양소
        "flavors": [],            # 맛 데이터
        "supplement_types": [],   # 영양제 종류
        "quantities": [],         # 수량
        "forms": [],              # 양식 (알약, 캡슐 등)
        "order_ratings": None,    # 별점 평점
        "order_reviewcnt": None,  # 리뷰 수
        "prices": [],             # 가격
        "origins": [],            # 원산지 국가
        "is_vegan": None,         # 비건 여부
        "purpose_tag": []         # 사용자의 목적 태그
    }

    # 모든 카테고리의 리스트 정의
    nutrient_lst = [
        "비타민 A","베타카로틴","비타민 D","비타민 E","비타민 K","비타민 B1","비타민 B2",
        "나이아신","판토텐산","비타민 B6","엽산","비타민 B12","비오틴","비타민 C","칼슘", "마그네슘",
        "철","아연","구리","셀레늄","요오드","망간","몰리브덴","칼륨","크롬","루테인","인",
        "메티오닌","시스테인","류신","트립토판","라이신","트레오닌","페닐알라닌","티로신"
    ]

    taste_lst = [
        "오렌지","복숭아","베리","망고","체리","딸기","파인애플",
        "바나나","멜론","포도","사과","키위","수박"
    ]

    type_lst = [
        "비타민 A","베타카로틴","비타민 D","비타민 E","비타민 K","비타민 B1","비타민 B2",
        "나이아신","판토텐산","비타민 B6","엽산","비타민 B12","비오틴","비타민 C","칼슘", "마그네슘",
        "철","아연","구리","셀레늄","요오드","망간","몰리브덴","칼륨","크롬","루테인","인",
        "메티오닌","시스테인","류신","트립토판","라이신","트레오닌","페닐알라닌","티로신","멀티비타민"
    ]

    form_lst = [
        "알약","캡슐","젤리","분말","젤","캔디","액상"
    ]

    purpose_tag_lst = [
        "간","기분","근육","눈","면역","뼈","소화",
        "수면","수분","신경","성장","집중","피부","혈당",
        "혈액","항산화","해독","피로회복"
    ]

    # 통합 시스템 프롬프트
    system_prompt = f"""당신은 사용자의 영양제 관련 텍스트에서 다양한 정보를 추출하는 전문가입니다.

사용자 텍스트를 분석하여 다음 정보들을 추출해주세요:

1. **영양소**: {', '.join(nutrient_lst)}
2. **맛**: {', '.join(taste_lst)}
3. **영양제 종류**: {', '.join(type_lst)}
4. **양식**: {', '.join(form_lst)}
5. **건강 목적**: {', '.join(purpose_tag_lst)}
6. **수량**: 영양제 개수 관련 숫자만 (함유량 제외)
7. **가격**: 가격 범위나 조건 (예: "2만원 이하", "저렴한")
8. **원산지**: 국가명이나 지역명
9. **별점 선호도**: 높은 별점순을 원하는지 (true/false/null)
10. **리뷰수 선호도**: 많은 리뷰수순을 원하는지 (true/false/null)
11. **비건 선호도**: 비건 제품을 원하는지 (true/false/null)

**추출 규칙:**
- 명시적으로 언급된 항목만 추출
- 정확한 이름으로 매칭 (예: "비타민C" → "비타민 C")
- 리스트에 없는 항목은 포함하지 말것
- 불린 값: true(원함), false(명시적 거부), null(언급 없음)

**응답 형식 (JSON):**
{{
  "nutrients": ["항목1", "항목2"],
  "flavors": ["항목1", "항목2"],
  "supplement_types": ["항목1", "항목2"],
  "forms": ["항목1", "항목2"],
  "purpose_tag": ["항목1", "항목2"],
  "quantities": ["30", "60"],
  "prices": ["2만원 이하", "저렴한"],
  "origins": ["미국", "독일"],
  "order_ratings": true/false/null,
  "order_reviewcnt": true/false/null,
  "is_vegan": true/false/null
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # 결과를 extracted_info에 병합
        for key in extracted_info.keys():
            if key in result:
                extracted_info[key] = result[key]

    except Exception as e:
        print(f"통합 정보 추출 중 에러 발생: {e}")
        # 에러 발생 시 빈 정보로 초기화

    # 상태 변경사항만 반환
    return {"extracted_info": extracted_info}

# --------------------------
# 4. build_kag_query
# --------------------------
import re
import os
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_openai import ChatOpenAI

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
 - 건강 목적(purpose_tag) 필터링: (s:Supplement)-[:HAS_TAG]->(:Tag {{name: 건강 목적}})
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


# --------------------------
# 5. send_kag_query
# --------------------------
from neo4j import GraphDatabase

def send_kag_query(state: AgentState) -> Dict[str, Any]:
    # Neo4j 연결
    uri = "neo4j+ssc://4d5cd572.databases.neo4j.io"
    username = "neo4j"
    password = "Zx86I42iwxvqd5G2SUKdrLgDHuY62vhl037CfwnpgwY"
    driver = GraphDatabase.driver(uri, auth=(username, password))

    results = []
    with driver.session() as session:
        kag_query = state["kag_query"]
        query_results = session.run(kag_query)
        
        # Record 객체를 딕셔너리로 변환
        results = [record.data() for record in query_results]
        print(results)

    # 변경된 상태 필드만 반환
    return {"kag_results": results}


# --------------------------
# 6. rerank_agent
# --------------------------
def rerank_agent(state: AgentState) -> Dict[str, Any]:
    # 추천 시스템의 리랭크 코드가 추가될 예정입니다.
    # 여기서는 간단히 kag_results를 그대로 반환
    return {"rerank_results": state["kag_results"]}


# --------------------------
# 7. select_product
# --------------------------
def select_product(state: AgentState) -> Dict[str, Any]:
    # 어떤 코드가 추가될 예정입니다.
    # 여기서는 간단히 rerank_results를 그대로 반환
    return {"final_results": state["rerank_results"]}


# --------------------------
# 8. final_answer
# --------------------------
def final_answer(state: AgentState) -> Dict[str, Any]:
    """
    모든 처리된 정보를 바탕으로 최종 영양제 추천 답변을 생성하는 Agent
    """
    from Product.models import Products

    # 상태에서 필요한 정보 추출
    user_query = state.get("user_query", "")
    user_health_info = state.get("user_health_info", {})
    extracted_info = state.get("extracted_info", {})
    kag_query = state.get("kag_query", "")
    kag_results = state.get("kag_results", [])
    rerank_results = state.get("rerank_results", {})
    final_results = state.get("final_results", {})

    # KAG 검색 결과에서 상품 ID를 추출
    product_ids = []
    simplified_product_details = []
    
    if kag_results:
        for result in kag_results:
            try:
                product_id = result.get('s.id')
                if product_id:
                    # 상품 ID 리스트에 추가
                    product_ids.append(product_id)
                    
                    # Products 모델에서 해당 ID의 상품 정보 조회 (LLM 응답 생성용)
                    product = Products.objects.get(id=product_id)
                    # LLM에게 전달할 간소화된 product_details (필요한 정보만 포함)
                    simplified_product_details.append({
                        'title': product.title,
                        'brand': product.brand,
                        'average_rating': product.average_rating,
                        'total_reviews': product.total_reviews,
                        'ingredients': product.ingredients,
                        'supplement_type': product.supplement_type,
                        'product_form': product.product_form,
                        'vegan': product.vegan,
                        'directions': product.directions,
                        'safety_info': product.safety_info
                    })
            except Products.DoesNotExist:
                print(f"상품 ID {product_id}에 해당하는 제품을 찾을 수 없습니다.")
            except Exception as e:
                print(f"상품 정보 조회 중 오류 발생: {e}")
    
    # 최종 답변 생성을 위한 시스템 프롬프트
    system_prompt = f"""당신은 개인 맞춤형 영양제 추천 전문가입니다.

**역할**: 사용자의 건강 상태와 요구사항을 종합적으로 분석하여 최적의 영양제를 추천하고, 그 이유를 명확하게 설명해주세요.

**출력 형식**:
1. **인사말**: "[사용자 이름]님, 건강 상태와 요구사항을 분석한 결과 다음 영양제를 추천해 드립니다." 로 시작하세요.

2. **추천 이유**:
   - 사용자의 건강 상태 분석 결과
   - 요구사항과의 부합도
   - 기대 효과

3. **추가 조언**:
   - 생활 습관 개선 제안

**중요 사항**:
- 제품에 대한 설명은 생략하세요
- 간결하고 명확하게 작성하세요
- 사용자의 건강 정보를 반영한 맞춤형 조언을 제공하세요

**톤**: 친근하고 전문적이며, 사용자가 이해하기 쉽게 설명해주세요."""

    # 사용자 정보 요약
    user_context = f"""
**사용자 질문**: {user_query}

**건강 정보 요약**:
{json.dumps(user_health_info, ensure_ascii=False, indent=2)}

**검색 결과 상세 정보**:
{json.dumps(simplified_product_details, ensure_ascii=False, indent=2) if simplified_product_details else "검색된 제품 정보 없음"}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        final_recommendation = response.choices[0].message.content

    except Exception as e:
        print(f"최종 답변 생성 중 에러 발생: {e}")
        final_recommendation = f"""죄송합니다. 추천 시스템에 일시적인 문제가 발생했습니다.

**사용자 요구사항 분석 결과**:
- 추출된 정보: {json.dumps(extracted_info, ensure_ascii=False)}
- 검색 결과: {len(product_ids)}개 제품 발견

전문 상담을 위해 약사나 의료진과 상의하시기 바랍니다."""

    # 변경된 상태 필드만 반환 (상품 상세 정보 대신 상품 ID 리스트만 반환)
    return {"final_recommendation": final_recommendation, "product_ids": product_ids}

