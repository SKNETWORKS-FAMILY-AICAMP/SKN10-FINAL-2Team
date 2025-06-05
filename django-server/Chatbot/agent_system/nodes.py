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


# --------------------------
# 2. extract_health_info
# --------------------------
def extract_health_info(state: AgentState) -> AgentState:
    """
    사용자 입력에서 건강 정보를 추출하여 기존 설문조사 데이터를 업데이트하는 함수

    Args:
        state: 현재 에이전트 상태
        - user_query: 사용자 입력
        - user_health_info: 기존 건강 정보 (설문조사 데이터)

    Returns:
        업데이트된 AgentState
        - user_health_info: 업데이트된 건강 정보
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

    # AgentState 업데이트 (기존 구조에 맞춤)
    updated_state = state.copy()
    updated_state["user_health_info"] = result.get("updated_health_info", current_health_data)

    return updated_state


# --------------------------
# 3. extract_comprehensive_info
# --------------------------
def extract_comprehensive_info(state: AgentState) -> AgentState:
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

        # 상태에 저장
        state["extracted_info"] = extracted_info

    except Exception as e:
        print(f"통합 정보 추출 중 에러 발생: {e}")
        # 에러 발생 시 빈 정보로 초기화
        state["extracted_info"] = extracted_info

    return state

# --------------------------
# 4. build_kag_query
# --------------------------
import re
def build_kag_query(state: AgentState) -> AgentState:
    """
    extracted_info를 바탕으로 그래프 DB Cypher 쿼리를 생성하는 Agent
    """

    extracted_info = state.get("extracted_info", {})

    # 그래프 DB 구조 설명
    graph_schema = """
    === Neo4j 그래프 DB 구조 ===

    **노드 타입:**
    1. Supplement: 영양제 제품
       - 속성: name, rating, review_count, price, is_vegan, quantity

    2. Nutrient: 영양소/성분
       - 속성: name, efficacy (효능 설명)

    3. Tag: 건강 목적 태그
       - 속성: name

    4. Form: 제형 (알약, 캡슐 등)
       - 속성: name

    5. Flavor: 맛 (딸기, 오렌지 등)
       - 속성: name

    6. Country: 원산지 국가
       - 속성: name

    7. Category: 제품 카테고리
       - 속성: name

    **관계 타입:**
    1. (:Supplement)-[:CONTAINS {amount: float, unit: string}]->(:Nutrient)
       - 영양제가 특정 영양소를 포함하는 관계
       - amount: 함유량, unit: 단위 (mg, μg 등)

    2. (:Supplement)-[:BELONGS_TO]->(:Category)
       - 영양제가 특정 카테고리에 속하는 관계

    3. (:Supplement)-[:HAS_FORM]->(:Form)
       - 영양제의 제형 관계

    4. (:Supplement)-[:HAS_FLAVOR]->(:Flavor)
       - 영양제의 맛 관계

    5. (:Nutrient)-[:HAS_TAG]->(:Tag)
       - 영양소가 특정 건강 목적 태그를 가지는 관계

    6. (:Supplement)-[:MADE_IN]->(:Country)
       - 영양제의 원산지 관계

    **주요 속성 값 예시:**
    - Supplement: is_vegan (true/false), rating (1.0-5.0), review_count (숫자), price (숫자), quantity (숫자)
    - Country.name: "독일", "미국", "한국" 등
    - Flavor.name: "딸기", "오렌지", "베리" 등
    - Form.name: "알약", "캡슐", "젤리" 등
    - Tag.name: "면역", "피로회복", "뼈건강" 등
    - Category.name: "멀티비타민", "비타민C" 등
    """

    # 쿼리 생성을 위한 시스템 프롬프트
    system_prompt = f"""{graph_schema}

위 그래프 DB 구조를 기반으로, 사용자의 요구사항에 맞는 Cypher 쿼리를 생성해주세요.

**쿼리 생성 규칙:**
1. MATCH 절에서 필요한 노드와 관계를 정의
2. WHERE 절에서 필터링 조건 적용:
   - nutrients: (:Supplement)-[:CONTAINS]->(:Nutrient) 관계로 특정 영양소 포함 필터링
   - supplement_types: (:Supplement)-[:BELONGS_TO]->(:Category) 관계로 카테고리 필터링
   - purpose_tag: (:Supplement)-[:CONTAINS]->(:Nutrient)-[:HAS_TAG]->(:Tag) 관계로 건강 목적 필터링
   - origins: (:Supplement)-[:MADE_IN]->(:Country) 관계로 원산지 필터링
   - flavors: (:Supplement)-[:HAS_FLAVOR]->(:Flavor) 관계로 맛 필터링
   - forms: (:Supplement)-[:HAS_FORM]->(:Form) 관계로 제형 필터링
   - quantities: Supplement.quantity 속성으로 수량 필터링
   - is_vegan: Supplement.is_vegan 속성으로 비건 여부 필터링
   - order_ratings: true면 높은 별점 우선 정렬
   - order_reviewcnt: true면 많은 리뷰수 우선 정렬
   - prices: "저렴한", "비싼" 등 텍스트를 가격 정렬로 변환

3. ORDER BY 절에서 우선순위 정렬:
   - order_ratings가 true면 s.rating DESC 추가
   - order_reviewcnt가 true면 s.review_count DESC 추가
   - prices 조건에 따라 s.price ASC/DESC 추가

4. LIMIT으로 결과 수 제한 (기본 20개)

5. RETURN 절에서 Supplement 속성 및 연결된 노드 정보 반환
   - 기본: s.name, s.rating, s.review_count, s.price, s.price_unit, s.is_vegan, s.quantity
   - 추가: 연결된 Country.name, Form.name, Flavor.name, Tag.name, Category.name 정보

**응답 형식:**
순수한 Cypher 쿼리문만 반환하세요. 설명이나 추가 텍스트 없이 쿼리만 작성해주세요.
"""

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

    if extracted_info.get("prices"):
        requirements.append(f"가격 조건: {', '.join(extracted_info['prices'])}")

    user_requirements = "사용자 요구사항:\n" + "\n".join(f"- {req}" for req in requirements)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_requirements}
        ],
        temperature=0.1
    )

    cypher_query = response.choices[0].message.content.strip()
    cypher_query = cypher_query.replace('```cypher', '').replace('```sql', '').replace('```', '').replace('`', '').strip()

    # 생성된 쿼리를 상태에 저장
    state["kag_query"] = cypher_query

    return state


# --------------------------
# 5. send_kag_query
# --------------------------
from neo4j import GraphDatabase

def send_kag_query(state: AgentState) -> AgentState:
    # Neo4j 연결
    uri = "neo4j+ssc://4d5cd572.databases.neo4j.io"
    username = "neo4j"
    password = "Zx86I42iwxvqd5G2SUKdrLgDHuY62vhl037CfwnpgwY"
    driver = GraphDatabase.driver(uri, auth=(username, password))

    with driver.session() as session:
        kag_query = state["kag_query"]
        results = session.run(kag_query)
        
        # Record 객체를 딕셔너리로 변환 (방법 1: data() 메서드 사용)
        state["kag_results"] = [record.data() for record in results]
        
        # 또는 방법 2: dict() 생성자 사용
        # state["kag_results"] = [dict(record) for record in results]
        print(state["kag_results"])

    return state


# --------------------------
# 6. rerank_agent
# --------------------------
def rerank_agent(state: AgentState) -> AgentState:
    # 추천 시스템의 리랭크 코드가 추가될 예정입니다.
    state["rerank_results"] = state["kag_results"]
    return state


# --------------------------
# 7. select_product
# --------------------------
def select_product(state: AgentState) -> AgentState:
    # 어떤 코드가 추가될 예정입니다.
    state["final_results"] = state["rerank_results"]
    return state


# --------------------------
# 8. final_answer
# --------------------------
def final_answer(state: AgentState) -> AgentState:
    """
    모든 처리된 정보를 바탕으로 최종 영양제 추천 답변을 생성하는 Agent
    """

    # 상태에서 필요한 정보 추출
    user_query = state.get("user_query", "")
    user_health_info = state.get("user_health_info", {})
    extracted_info = state.get("extracted_info", {})
    kag_query = state.get("kag_query", "")
    kag_results = state.get("kag_results", [])
    rerank_results = state.get("rerank_results", {})
    final_results = state.get("final_results", {})

    # KAG 검색 결과를 문자열로 변환
    kag_results_text = ""
    if kag_results:
        kag_results_text = "검색된 영양제 제품:\n"
        for i, record in enumerate(kag_results[:10], 1):  # 상위 10개만
            try:
                # Neo4j 레코드에서 데이터 추출
                supplement_data = dict(record)
                kag_results_text += f"{i}. {supplement_data}\n"
            except Exception as e:
                kag_results_text += f"{i}. 데이터 파싱 오류: {e}\n"
    else:
        kag_results_text = "검색된 제품이 없습니다."

    # 최종 답변 생성을 위한 시스템 프롬프트
    system_prompt = f"""당신은 개인 맞춤형 영양제 추천 전문가입니다.

**역할**: 사용자의 건강 상태와 요구사항을 종합적으로 분석하여 최적의 영양제를 추천하고, 그 이유를 명확하게 설명해주세요.

**추천 가이드라인**:
1. 사용자의 건강 정보와 생활 습관을 우선 고려
2. 알레르기와 복용 중인 약물과의 상호작용 주의
3. 사용자의 구체적인 요구사항 반영
4. 검색된 제품 중에서 가장 적합한 제품 선별
5. 복용법과 주의사항도 함께 안내

**답변 구조**:
1. **추천 제품** (상위 3-5개)
   - 제품명, 주요 성분, 별점
   - 왜 이 제품을 추천하는지 구체적 이유

2. **추천 이유**
   - 사용자 건강 상태 분석 결과
   - 요구사항과의 부합도
   - 제품의 장점

3. **복용 가이드**
   - 권장 복용법
   - 주의사항 (알레르기, 약물 상호작용 등)
   - 기대 효과와 소요 시간

4. **추가 조언**
   - 생활 습관 개선 제안

**톤**: 친근하고 전문적이며, 사용자가 이해하기 쉽게 설명해주세요."""

    # 사용자 정보 요약
    user_context = f"""
**사용자 질문**: {user_query}

**건강 정보 요약**:
{json.dumps(user_health_info, ensure_ascii=False, indent=2)}

**추출된 요구사항**:
{json.dumps(extracted_info, ensure_ascii=False, indent=2)}

**생성된 검색 쿼리**:
{kag_query}

**검색 결과 리랭크 및 최종 필터링 결과**:
{json.dumps(final_results, ensure_ascii=False, indent=2) if final_results else "최종 결과 없음"}
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
- 검색 결과: {len(kag_results)}개 제품 발견

전문 상담을 위해 약사나 의료진과 상의하시기 바랍니다."""

    # 상태 업데이트
    state["final_recommendation"] = final_recommendation

    return state

