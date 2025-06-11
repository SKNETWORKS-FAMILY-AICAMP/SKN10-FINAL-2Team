"""LangGraph multi-agent supervisor system with Human-in-the-loop.

Implements a supervisor agent system with specialized agents for nutrition and supplement information.
"""

from __future__ import annotations

import os
import json
from typing import Annotated, Dict, List, Any, TypedDict
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.types import interrupt, Command
from langgraph.prebuilt.interrupt import HumanInterrupt
from neo4j import GraphDatabase
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import InMemorySaver
import logging
from psycopg_pool import ConnectionPool
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenAI 클라이언트 초기화
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Initialize OpenAI client for LangChain
def get_llm(model_name="gpt-4o"):
    """Get LLM instance with appropriate configuration."""
    return ChatOpenAI(
        model=model_name,
        temperature=0.1
    )

# Neo4j connection
def get_neo4j_driver():
    """Get Neo4j database connection."""
    uri = "neo4j+ssc://4d5cd572.databases.neo4j.io"
    username = "neo4j"
    password = "Zx86I42iwxvqd5G2SUKdrLgDHuY62vhl037CfwnpgwY"
    return GraphDatabase.driver(uri, auth=(username, password))

# Create a function to execute Neo4j queries
def execute_neo4j_query(query, params=None):
    """Execute a Neo4j query and return the results."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(query, params)
        records = [record.data() for record in result]
        return records

# Define the agent state structure
class AgentState(TypedDict):
    """영양제 추천 에이전트의 상태를 정의하는 클래스"""
    user_query: str
    user_health_info: Dict[str, Any]
    extracted_info: Dict[str, Any]
    kag_query: str
    kag_results: List[Any]
    rerank_results: List[Any]
    final_results: List[Any]
    final_recommendation: str

# --------------------------
# Tools for nutrient assistant
# --------------------------

def query_nutrient_info(nutrient_name: str) -> str:
    """영양소에 대한 정보를 그래프 데이터베이스에서 조회합니다."""
    query = f"""
    MATCH (n:Nutrient {{name: $nutrient_name}})
    RETURN n.name as name, n.efficacy as efficacy
    """
    results = execute_neo4j_query(query, {"nutrient_name": nutrient_name})
    if results:
        return f"Found nutrient information: {results}"
    else:
        return f"No information found for nutrient: {nutrient_name}"

def query_nutrient_benefits(health_concern: str) -> str:
    """특정 건강 문제에 도움이 되는 영양소를 조회합니다."""
    query = f"""
    MATCH (n:Nutrient)-[:HAS_TAG]->(t:Tag {{name: $health_concern}})
    RETURN n.name as nutrient, t.name as health_concern
    """
    results = execute_neo4j_query(query, {"health_concern": health_concern})
    if results:
        return f"Nutrients that benefit {health_concern}: {results}"
    else:
        return f"No nutrients found that specifically benefit: {health_concern}"

def extract_health_info(state: Dict[str, Any]) -> str:
    """사용자 입력에서 건강 정보를 추출합니다."""
    user_query = state.get("user_query", "")
    current_health_data = state.get("user_health_info", {})
    
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
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    result = json.loads(content)
    
    return f"Extracted health information: {json.dumps(result.get('updated_health_info', {}), ensure_ascii=False)}"

# --------------------------
# Tools for supplement assistant
# --------------------------

def query_supplement_info(supplement_name: str) -> str:
    """영양제 제품에 대한 정보를 그래프 데이터베이스에서 조회합니다."""
    query = f"""
    MATCH (s:Supplement {{name: $supplement_name}})
    RETURN s.name as name, s.rating as rating, s.review_count as review_count, s.price as price, s.is_vegan as is_vegan
    """
    results = execute_neo4j_query(query, {"supplement_name": supplement_name})
    if results:
        return f"Found supplement information: {results}"
    else:
        return f"No information found for supplement: {supplement_name}"

def query_supplements_for_nutrient(nutrient_name: str) -> str:
    """특정 영양소를 포함하는 영양제를 조회합니다."""
    query = f"""
    MATCH (s:Supplement)-[:CONTAINS]->(n:Nutrient {{name: $nutrient_name}})
    RETURN s.name as supplement, n.name as nutrient
    """
    results = execute_neo4j_query(query, {"nutrient_name": nutrient_name})
    if results:
        return f"Supplements containing {nutrient_name}: {results}"
    else:
        return f"No supplements found containing: {nutrient_name}"

def build_kag_query(query_text: str) -> str:
    """사용자 쿼리를 기반으로 그래프 데이터베이스 쿼리를 생성합니다."""
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
    2. (:Supplement)-[:BELONGS_TO]->(:Category)
    3. (:Supplement)-[:HAS_FORM]->(:Form)
    4. (:Supplement)-[:HAS_FLAVOR]->(:Flavor)
    5. (:Nutrient)-[:HAS_TAG]->(:Tag)
    6. (:Supplement)-[:MADE_IN]->(:Country)
    """
    
    system_prompt = f"""{graph_schema}

위 그래프 DB 구조를 기반으로, 사용자의 요구사항에 맞는 Cypher 쿼리를 생성해주세요.
사용자 요구사항을 분석하여 적절한 필터링과 정렬 조건을 포함한 쿼리를 작성하세요.
순수한 Cypher 쿼리문만 반환하세요. 설명이나 추가 텍스트 없이 쿼리만 작성해주세요.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"사용자 요구사항: {query_text}"}
        ],
        temperature=0.1
    )

    cypher_query = response.choices[0].message.content.strip()
    cypher_query = cypher_query.replace('```cypher', '').replace('```sql', '').replace('```', '').replace('`', '').strip()
    
    return f"Generated Cypher query: {cypher_query}"

def send_kag_query(cypher_query: str) -> str:
    """생성된 Cypher 쿼리를 Neo4j 데이터베이스에 전송합니다."""
    try:
        # 쿼리에서 실제 Cypher 부분만 추출
        if "Generated Cypher query:" in cypher_query:
            cypher_query = cypher_query.split("Generated Cypher query:")[1].strip()
        
        results = execute_neo4j_query(cypher_query)
        return f"Query results: {json.dumps(results[:5], ensure_ascii=False)}"  # 결과가 너무 많을 수 있으므로 처음 5개만 반환
    except Exception as e:
        return f"Error executing query: {str(e)}"

def rerank_supplements(supplements: list[str]) -> str:
    """영양제 추천 결과를 사용자 프로필에 맞게 재정렬합니다."""
    return f"Reranked supplements based on user profile: {supplements}"

# --------------------------
# Human-in-the-loop functionality
# --------------------------

def add_human_in_the_loop(tool):
    """Wrapper to add human-in-the-loop functionality to any tool."""
    def call_tool_with_interrupt(*args, **kwargs):
        """Wrapper function that adds human-in-the-loop functionality to a tool."""
        # Create a human interrupt with tool information
        tool_name = tool.__name__
        tool_args = args if args else kwargs
        
        # Interrupt execution and wait for human input
        response = interrupt([
            HumanInterrupt(
                type="tool_call",
                data={
                    "name": tool_name,
                    "args": tool_args,
                    "description": tool.__doc__ or ""
                }
            )
        ])
        
        # Process the human response
        if isinstance(response, Command) and hasattr(response, "resume"):
            resume_data = response.resume[0]
            if resume_data["type"] == "accept":
                # Human approved, execute the original tool
                return tool(*args, **kwargs)
            elif resume_data["type"] == "edit":
                # Human edited the arguments, execute with new args
                new_args = resume_data["args"]["args"]
                if isinstance(new_args, dict):
                    return tool(**new_args)
                else:
                    return tool(*new_args)
            elif resume_data["type"] == "reject":
                # Human rejected the tool call
                return "Tool call was rejected by the human."
            else:
                raise ValueError(f"Unsupported interrupt response type: {resume_data['type']}")
        
        return "No response received from human."
    
    # Make sure the wrapper has a docstring
    call_tool_with_interrupt.__doc__ = f"Human-in-the-loop wrapper for {tool.__name__}: {tool.__doc__}"
    
    return call_tool_with_interrupt

def request_user_info(question: str) -> str:
    """사용자에게 추가 정보를 요청합니다."""
    response = interrupt([
        HumanInterrupt(
            type="user_request",
            data={
                "question": question
            }
        )
    ])
    
    if isinstance(response, Command) and hasattr(response, "resume"):
        return response.resume[0].get("answer", "No answer provided")
    
    return "No response received from user."

# --------------------------
# PostgreSQL 연결 풀 관리
# --------------------------

_db_pool = None

def get_db_connection_pool():
    """
    PostgreSQL 데이터베이스 연결 풀을 생성하고 반환합니다.
    한 번만 생성되며, 이후 호출에서는 기존 풀을 반환합니다.
    """
    global _db_pool
    if _db_pool is None:
        # 환경변수에서 DB 연결 정보를 가져오거나, 기본값 사용
        db_uri = os.environ.get("POSTGRES_URI")
        if not db_uri:
            db_host = os.environ.get("POSTGRES_HOST", "localhost")
            db_port = os.environ.get("POSTGRES_PORT", "5432")
            db_name = os.environ.get("POSTGRES_DB", "topDB")
            db_user = os.environ.get("POSTGRES_USER", "topAdmin")
            db_password = os.environ.get("POSTGRES_PASSWORD", "root1234")
            db_uri = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        connection_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
        }
        
        # 커넥션 풀 생성
        _db_pool = ConnectionPool(
            conninfo=db_uri,
            max_size=20,
            kwargs=connection_kwargs,
        )
        logger.info("PostgreSQL connection pool created.")
    
    return _db_pool

# Create a checkpointer for persistence
def get_checkpointer():
    """Get the appropriate checkpointer based on environment configuration."""
    try:
        # PostgreSQL 연결 풀 가져오기
        pool = get_db_connection_pool()
        
        # PostgreSQL 체크포인터 생성
        logger.info("Creating PostgreSQL checkpointer...")
        checkpointer = PostgresSaver(pool)
        
        # 테이블 생성 등 필요한 초기 설정
        checkpointer.setup()
        logger.info("PostgreSQL checkpointer setup completed.")
        
        return checkpointer
    except Exception as e:
        # 오류 발생 시 InMemorySaver로 폴백
        logger.warning(f"Failed to setup PostgreSQL checkpointer: {e}")
        logger.info("Falling back to InMemorySaver")
        return InMemorySaver()

# Get the appropriate checkpointer
checkpointer = get_checkpointer()

# --------------------------
# Create the specialized agents
# --------------------------

nutrient_assistant = create_react_agent(
    model="openai:gpt-4o",
    tools=[
        query_nutrient_info, 
        query_nutrient_benefits,
        extract_health_info
    ],
    prompt="""You are a nutrient assistant specialized in providing information about nutrients.
    Your job is to query the graph database to find information about nutrients, their benefits,
    and their relationship to health concerns. Be precise and scientific in your responses.
    You can also extract health information from user queries to better understand their needs.""",
    name="nutrient_assistant",
    checkpointer=checkpointer
)

supplement_assistant = create_react_agent(
    model="openai:gpt-4o",
    tools=[
        query_supplement_info, 
        query_supplements_for_nutrient,
        build_kag_query,
        send_kag_query,
        rerank_supplements
    ],
    prompt="""You are a supplement assistant specialized in providing information about supplement products.
    Your job is to query the graph database to find information about supplements, their ingredients,
    dosage recommendations, and safety warnings. Be precise and scientific in your responses.
    You can build and send queries to the graph database to find relevant supplements.""",
    name="supplement_assistant",
    checkpointer=checkpointer
)

request_info_assistant = create_react_agent(
    model="openai:gpt-4o",
    tools=[add_human_in_the_loop(request_user_info)],
    prompt="""You are a request info assistant specialized in gathering additional information from users.
    When the supervisor needs more details to provide accurate recommendations, your job is to ask
    clear, specific questions to the user. Focus on gathering health goals, current supplements,
    dietary restrictions, and health concerns.""",
    name="request_info_assistant",
    checkpointer=checkpointer
)

final_answer_assistant = create_react_agent(
    model="openai:gpt-4o",
    tools=[],
    prompt="""You are a final answer assistant specialized in synthesizing information from multiple sources.
    Your job is to take the information gathered by the nutrient assistant, supplement assistant,
    and any user information, and create a comprehensive, easy-to-understand response that addresses
    the user's original query. Be helpful, accurate, and provide actionable recommendations.""",
    name="final_answer_assistant",
    checkpointer=checkpointer
)

# --------------------------
# Create the supervisor agent
# --------------------------

graph = create_supervisor(
    agents=[
        nutrient_assistant, 
        supplement_assistant, 
        request_info_assistant, 
        final_answer_assistant
    ],
    model=get_llm(),
    prompt="""You are a supervisor managing a team of specialized agents to help users with nutrition and supplement information.

    Your team consists of:
    1. nutrient_assistant: Specialized in nutrient information from the graph database and extracting health information
    2. supplement_assistant: Specialized in supplement product information from the graph database and building/sending queries
    3. request_info_assistant: Specialized in gathering additional information from the user when needed
    4. final_answer_assistant: Specialized in synthesizing information and providing final responses

    Your job is to:
    1. Analyze the user's query to determine what information is needed
    2. Use request_info_assistant when the user query lacks specific details needed for recommendations
    3. Delegate nutrient-related queries to the nutrient_assistant
    4. Delegate supplement-related queries to the supplement_assistant
    5. Once all necessary information is gathered, use final_answer_assistant to provide a comprehensive response

    Always ensure you have sufficient information before making recommendations. User health and safety is the priority.
    
    Work through the problem step by step:
    1. First, understand what the user is asking for (nutrient_assistant can help extract health info)
    2. If information is missing, ask the user (request_info_assistant)
    3. Search for appropriate supplements (supplement_assistant)
    4. Provide a final recommendation (final_answer_assistant)"""
).compile()

# --------------------------
# Example usage
# --------------------------

def run_agent(user_query: str):
    """Run the agent with a user query."""
    config = {"configurable": {"thread_id": "1"}}
    
    for chunk in graph.stream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_query
                }
            ]
        },
        config
    ):
        print(chunk)
        print("\n")

# 애플리케이션 종료 시 자원 정리
def cleanup():
    """애플리케이션 종료 시 자원을 정리합니다."""
    global _db_pool
    if _db_pool is not None:
        _db_pool.close()
        logger.info("PostgreSQL connection pool closed.")

# For testing
if __name__ == "__main__":
    try:
        run_agent("What supplements should I take for better sleep?")
    finally:
        cleanup()
