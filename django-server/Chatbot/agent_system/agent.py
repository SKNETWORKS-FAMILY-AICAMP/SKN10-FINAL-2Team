from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 노드 함수 직접 임포트 (패키지 초기화 파일 사용하지 않음)
from .state import AgentState

# 영양제 관련 노드들 import
from .node.input_analysis import analyze_input
from .node.general_chat import handle_general_chat
from .node.supplement.extract import is_personalized_supplement, is_enough_supplement_info, extract_supplement_info
from .node.supplement.query import search_personal_sup, search_nonpersonal_sup
from .node.supplement.rerank import rerank_node, select_products_node
from .node.supplement.response import summary_node_process, generate_supplement_response

# 영양소 관련 노드들 import
from .node.nutrient.extract import extract_nutrient_info
from .node.nutrient.knowledge import search_nutrient_knowledge
from .node.nutrient.response import generate_nutrient_response

# PostgreSQL 영속성 체크포인터 관련 모듈 추가
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

class SupplementRecommendationAgent:
    """
    영양소 및 영양제 추천 Agent 시스템을 관리하는 클래스.
    LangGraph 워크플로우를 캡슐화하고, 애플리케이션 생명주기 동안
    한 번만 초기화되도록 합니다.
    """
    _workflow = None  # 워크플로우 인스턴스를 저장할 클래스 변수
    _pool = None  # DB 커넥션 풀을 저장할 클래스 변수

    @classmethod
    def create_supplement_recommendation_workflow(cls):
        """
        apps.py에서 호출하는 메서드.
        내부적으로 create_workflow 메서드를 호출합니다.
        """
        return cls.create_workflow()

    @classmethod
    def get_db_connection_pool(cls):
        """
        PostgreSQL 데이터베이스 연결 풀을 생성하고 반환합니다.
        한 번만 생성되며, 이후 호출에서는 기존 풀을 반환합니다.
        """
        if cls._pool is None:
            # 환경변수에서 DB 연결 정보를 가져오거나, 기본값 사용
            db_uri = os.getenv("POSTGRES_URI")
            
            connection_kwargs = {
                "autocommit": True,
                "prepare_threshold": 0,
            }
            
            # 커넥션 풀 생성 - 최대 20개의 연결 유지
            cls._pool = ConnectionPool(
                conninfo=db_uri,
                max_size=20,
                kwargs=connection_kwargs,
            )
            print("PostgreSQL connection pool created.")
        
        return cls._pool

    @classmethod
    def create_workflow(cls):
        """
        영양소 및 영양제 추천 시스템의 전체 워크플로우를 생성하고 컴파일합니다.
        이 메서드는 워크플로우가 아직 초기화되지 않았을 때만 실행됩니다.
        PostgreSQL 체크포인터를 사용하여 상태 영속성을 제공합니다.
        """
        if cls._workflow is None:
            # 조건 함수 정의
            def route_by_conversation_type(state: AgentState):
                conversation_type = state.get("conversation_type", "general")
                return conversation_type
            
            def route_by_is_enough_supplement_info(state: AgentState):
                return "enough" if state.get("is_enough_sup_info", False) else "not_enough"
            
            def route_by_is_enough_nutrient_info(state: AgentState):
                return "enough" if state.get("is_enough_nut_info", False) else "not_enough"
            
            def route_by_is_personalized(state: AgentState):
                return "personalized" if state.get("is_personalized", False) else "non_personalized"
            
            # 시작점 설정!
            builder = StateGraph(AgentState)
            
            # 분기 처리 노드 (작업 완료!)
            builder.add_node("analyze_input", analyze_input)

            # 일반 대화 처리 노드 (작업 완료!)
            builder.add_node("general_chat", handle_general_chat)

            # 영양제 관련 노드
            builder.add_node("is_personalized_supplement", is_personalized_supplement)
            builder.add_node("is_enough_supplement_info", is_enough_supplement_info)
            builder.add_node("extract_supplement_info", extract_supplement_info)  # 함수명 매핑
            builder.add_node("search_personal_sup", search_personal_sup)
            builder.add_node("search_nonpersonal_sup", search_nonpersonal_sup)  # 함수명 매핑
            builder.add_node("rerank_node", rerank_node)  # 노드 이름 변경
            builder.add_node("select_products_node", select_products_node)  # 노드 이름 변경
            builder.add_node("summary_node_process", summary_node_process)
            builder.add_node("generate_supplement_response", generate_supplement_response)  # 함수명 매핑
            
            # 영양소 관련 노드
            builder.add_node("extract_nutrient_info", extract_nutrient_info)
            builder.add_node("search_nutrient_knowledge", search_nutrient_knowledge)
            builder.add_node("generate_nutrient_response", generate_nutrient_response)
            
            # 엣지 연결
            # 입력 분석 후 분기
            builder.add_conditional_edges(
                "analyze_input",
                route_by_conversation_type,
                {
                    "general": "general_chat",
                    "nutrient": "extract_nutrient_info",
                    "supplement": "is_enough_supplement_info"
                }
            )

            builder.add_conditional_edges(
                "is_enough_supplement_info",
                route_by_is_enough_supplement_info,
                {
                    "enough": "extract_supplement_info",
                    "not_enough": END
                }
            )

            builder.add_conditional_edges(
                "extract_nutrient_info",
                route_by_is_enough_nutrient_info,
                {
                    "enough": "search_nutrient_knowledge",
                    "not_enough": END
                }
            )

            builder.add_conditional_edges(
                "is_personalized_supplement",
                route_by_is_personalized,
                {
                    "personalized": "search_personal_sup",
                    "non_personalized": "search_nonpersonal_sup"
                }
            )
            
            # 일반 대화 처리 후 종료
            builder.add_edge("general_chat", END)
            
            # 영양제 추천 플로우
            builder.add_edge("extract_supplement_info", "is_personalized_supplement")
            builder.add_edge("search_personal_sup", "rerank_node")
            builder.add_edge("search_nonpersonal_sup", "rerank_node")
            builder.add_edge("rerank_node", "select_products_node")
            builder.add_edge("select_products_node", "summary_node_process")
            builder.add_edge("summary_node_process", "generate_supplement_response")
            builder.add_edge("generate_supplement_response", END)

            # 영양소 설명 플로우
            builder.add_edge("search_nutrient_knowledge", "generate_nutrient_response")
            builder.add_edge("generate_nutrient_response", END)

            # 시작점 설정
            builder.set_entry_point("analyze_input")

            # PostgreSQL 체크포인터 설정
            pool = cls.get_db_connection_pool()
            checkpointer = PostgresSaver(pool)
            
            # 테이블 생성 등 필요한 초기 설정
            checkpointer.setup()
            print("PostgreSQL checkpointer setup completed.")

            # workflow 컴파일
            cls._workflow = builder.compile(
                checkpointer=checkpointer
            )
            print("LangGraph workflow compiled with PostgreSQL persistence.")

        print(cls._workflow.get_graph().draw_mermaid())
        return cls._workflow

    @classmethod
    def get_workflow(cls):
        """
        초기화된 LangGraph 워크플로우 인스턴스를 반환합니다.
        필요하다면 이 메서드를 통해 워크플로우를 초기화합니다.
        """
        if cls._workflow is None:
            cls.create_workflow()
        return cls._workflow
    
    @classmethod
    def get_thread_config(cls, thread_id):
        """
        특정 스레드 ID에 대한 구성을 반환합니다.
        이를 통해 각 사용자(스레드)별로 상태를 분리하여 관리합니다.
        """
        return {"configurable": {"thread_id": str(thread_id)}}
    
    @classmethod
    def process_message(cls, thread_id: str, message: str, user_id: int, user_health_info: Optional[Dict[str, Any]] = None):
        """
        사용자 메시지를 처리하고 응답을 생성합니다.
        
        Args:
            thread_id: 사용자 스레드 ID
            message: 사용자 메시지
            user_health_info: 사용자 건강 정보 (선택적)
            
        Returns:
            응답 텍스트와 후속 질문을 포함하는 딕셔너리
        """
        import time

        # 워크플로우, 스레드 구성 가져오기
        workflow = cls.get_workflow()
        config = cls.get_thread_config(thread_id)
        
        # 질문이 들어올 때마다 주요 state 필드 초기화
        workflow.update_state(config, {
            "response": "",
            "node_messages": [],
            "node_messages_summary": "",
            "conversation_type": None,
            "is_personalized": False,
            "is_enough_sup_info": False,
            "extracted_info": {},
            "personalized_info": {},
            "kag_query": None,
            "kag_results": [],
            "rerank_results": [],
            "final_results": [],
            "product_ids": [],
            "followup_question": "",
            "is_enough_nut_info": False,
            "nutrients": [],
            "nutrient_knowledge": {}
        })

        # 기존 상태 가져오기 (LangGraph checkpointer가 자동으로 관리)

        # 기존 상태 조회 시도
        existing_state = workflow.get_state(config)
        print(f"기존 상태 조회 성공: {thread_id}")
        print(f"기존 상태: {existing_state.next}")
        workflow.update_state(config, {"user_id": user_id})

        # 이전대화에서 추천된 product_ids 초기화
        workflow.update_state(config, {"product_ids": []})

        # 이전대화에서 사용된 state 초기화
        workflow.update_state(config, {"personalized_info": {}})

        if user_health_info:
            workflow.update_state(config, {"user_health_info": user_health_info})
        
        if existing_state.next and len(existing_state.next) > 0:
            print("체크포인트에서 재시작 중...")

            # 새로운 사용자 메시지 추가
            workflow.update_state(config, {"messages": [HumanMessage(content=message)]})
            
            try:
                for event in workflow.stream(None, config=config, stream_mode="values"):
                    if event.get("messages"):
                        event["messages"][-1].pretty_print()
            except Exception as e:
                print(f"재시작 중 오류 발생: {e}")
        else:
            print("새로운 대화 시작")
            # 새로운 대화 시작
            initial_state = {"messages": [HumanMessage(content=message)]}
            
            try:
                for event in workflow.stream(initial_state, config=config, stream_mode="values"):
                    if event.get("messages"):
                        event["messages"][-1].pretty_print()
            except Exception as e:
                print(f"새로운 대화 중 오류 발생: {e}")

        # 최종 상태 가져오기
        final_state = workflow.get_state(config)
        print(f"최종 상태: {final_state.values}")
        result = final_state.values

        # 응답 추출
        response = result.get("response", "")
        product_ids = result.get("product_ids", "")
        followup_question = result.get("followup_question", "")
        needs_human_input = result.get("needs_human_input", False)
        print(f"최종 응답: {response}")

        return {
            "response": response,
            "followup_question": followup_question,
            "needs_human_input": needs_human_input,
            "product_ids": product_ids
        }
    
    @classmethod
    def cleanup(cls):
        """
        애플리케이션 종료 시 자원을 정리합니다.
        """
        if cls._pool is not None:
            cls._pool.close()
            print("PostgreSQL connection pool closed.")