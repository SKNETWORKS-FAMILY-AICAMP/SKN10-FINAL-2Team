from typing import Dict, Any, Optional, List
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 노드 함수 직접 임포트 (패키지 초기화 파일 사용하지 않음)
from .state import AgentState, UserHealthInfo, ExtractedInfo, QueryResult, NutrientKnowledge, NutrientSummary

from .node.input_analysis import analyze_input
from .node.general_chat import handle_general_chat
from .node.supplement.extract import extract_health_info, extract_supplement_info
from .node.supplement.query import build_kag_query, execute_kag_query
from .node.supplement.rerank import rerank_node, select_products_node
from .node.supplement.response import generate_supplement_response

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
            
            # StateGraph 생성 및 노드 추가 (LangGraph 공식 방식)
            builder = StateGraph(AgentState)
            
            # 노드 추가 - nodes.py에서 가져온 함수들로 대체
            builder.add_node("analyze_input", analyze_input)

            # 일반 대화 처리 노드
            builder.add_node("general_chat", handle_general_chat)
            
            # 영양소 관련 노드

            
            # 영양제 관련 노드
            builder.add_node("extract_health_info", extract_health_info)
            builder.add_node("extract_supplement_info", extract_supplement_info)  # 함수명 매핑
            builder.add_node("build_kag_query", build_kag_query)
            builder.add_node("execute_kag_query", execute_kag_query)  # 함수명 매핑
            builder.add_node("rerank_node", rerank_node)  # 노드 이름 변경
            builder.add_node("select_products_node", select_products_node)  # 노드 이름 변경
            builder.add_node("generate_supplement_response", generate_supplement_response)  # 함수명 매핑
            
            # 엣지 연결
            # 입력 분석 후 분기
            builder.add_conditional_edges(
                "analyze_input",
                route_by_conversation_type,
                {
                    "general": "general_chat",
                    "nutrient": "extract_health_info",  # 영양소 노드 제거로 임시 변경
                    "supplement": "extract_health_info"
                }
            )
            # # 추가 정보 요청 분기
            # builder.add_conditional_edges(
            #     "extract_supplement_info",
            #     check_human_input_needed,
            #     {
            #         "needs_input": END,  # 사용자 입력 대기
            #         "continue": "build_kag_query"  # 다음 단계로
            #     }
            # )
            
            # 일반 대화 처리 후 종료
            builder.add_edge("general_chat", END)
            
            # 영양제 추천 플로우 (단순화)
            builder.add_edge("extract_health_info", "extract_supplement_info")
            # builder.add_edge("extract_supplement_info", "build_kag_query")
            builder.add_edge("build_kag_query", "execute_kag_query")
            builder.add_edge("execute_kag_query", "rerank_node")
            builder.add_edge("rerank_node", "select_products_node")
            builder.add_edge("select_products_node", "generate_supplement_response")
            builder.add_edge("generate_supplement_response", END)

            # 시작점 설정
            builder.set_entry_point("analyze_input")

            try:
                # PostgreSQL 체크포인터 설정
                pool = cls.get_db_connection_pool()
                checkpointer = PostgresSaver(pool)
                
                # 테이블 생성 등 필요한 초기 설정
                checkpointer.setup()
                print("PostgreSQL checkpointer setup completed.")

                # interrupt_after를 사용하여 extract_supplement_info 노드 실행 후에 
                # NodeInterrupt가 발생했는지 체크
                cls._workflow = builder.compile(
                    checkpointer=checkpointer,
                    interrupt_after=["extract_supplement_info"]
                )
                print("LangGraph workflow compiled with PostgreSQL persistence.")
            except Exception as e:
                print(f"Failed to setup PostgreSQL checkpointer: {e}")
                # 체크포인터 없이 컴파일 (폴백)
                cls._workflow = builder.compile(
                    interrupt_before=["build_kag_query"]
                )
                print("LangGraph workflow compiled without persistence (fallback mode).")
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
    def process_message(cls, thread_id: str, message: str, user_health_info: Optional[Dict[str, Any]] = None):
        """
        사용자 메시지를 처리하고 응답을 생성합니다.
        
        Args:
            thread_id: 사용자 스레드 ID
            message: 사용자 메시지
            user_health_info: 사용자 건강 정보 (선택적)
            
        Returns:
            응답 텍스트와 후속 질문을 포함하는 딕셔너리
        """
        # 워크플로우, 스레드 구성 가져오기
        workflow = cls.get_workflow()
        config = cls.get_thread_config(thread_id)
        
        # 기존 상태 가져오기 (LangGraph checkpointer가 자동으로 관리)
        try:
            # 기존 상태 조회 시도
            existing_state = workflow.get_state(config)
            print(f"기존 상태 조회 성공: {thread_id}")
            print(f"기존 상태: {existing_state.next}")

            # interrupt 상태에서 재시작하는 경우
            if existing_state.next and len(existing_state.next) > 0:
                print("체크포인트에서 재시작 중...")
                # 새로운 사용자 메시지 추가
                workflow.update_state(config, {"messages": [HumanMessage(content=message)]})
                
                try:
                    # None을 전달하여 체크포인트부터 재시작
                    for event in workflow.stream(None, config=config, stream_mode="values"):
                        if event.get("messages"):
                            event["messages"][-1].pretty_print()
                except Exception as e:
                    # NodeInterrupt가 다시 발생할 수 있음
                    print(f"재시작 중 interrupt 발생: {e}")
            else:
                print("새로운 대화 시작")
                # 새로운 대화 시작
                initial_state = {"messages": [HumanMessage(content=message)]}
                if user_health_info:
                    initial_state["user_health_info"] = user_health_info
                
                try:
                    for event in workflow.stream(initial_state, config=config, stream_mode="values"):
                        if event.get("messages"):
                            event["messages"][-1].pretty_print()
                except Exception as e:
                    print(f"새로운 대화 중 interrupt 발생: {e}")
        except Exception as e:
            print(f"상태 처리 중 오류: {e}")
            # 새로운 대화로 처리
            initial_state = {"messages": [HumanMessage(content=message)]}
            if user_health_info:
                initial_state["user_health_info"] = user_health_info
            
            try:
                for event in workflow.stream(initial_state, config=config, stream_mode="values"):
                    if event.get("messages"):
                        event["messages"][-1].pretty_print()
            except Exception as e:
                print(f"폴백 처리 중 interrupt 발생: {e}")

        # 최종 상태 가져오기
        final_state = workflow.get_state(config)
        result = final_state.values

        # interrupt 상태 확인
        is_interrupted = len(final_state.next) > 0 if final_state.next else False

        # 응답 추출
        final_recommendation = result.get("final_recommendation", "")
        product_ids = result.get("product_ids", "")
        followup_question = result.get("followup_question", "")
        needs_human_input = result.get("needs_human_input", False)
        human_input_request = result.get("human_input_request", "")

        # interrupt가 발생한 경우 interrupt 메시지 확인
        interrupt_message = ""
        if is_interrupted and hasattr(final_state, 'tasks') and final_state.tasks:
            # NodeInterrupt의 메시지 추출
            for task in final_state.tasks:
                if hasattr(task, 'interrupts') and task.interrupts:
                    interrupt_message = str(task.interrupts[0])
                    break


        # interrupt 발생 시에는 AI 메시지를 추가하지 않음 (재시작 시 문제 방지)
        if not is_interrupted and final_recommendation:
            workflow.update_state(config, {"messages": [AIMessage(content=final_recommendation)]})
        elif is_interrupted and interrupt_message:
            # interrupt 메시지를 AI 메시지로 추가
            workflow.update_state(config, {"messages": [AIMessage(content=interrupt_message)]})

        # 응답 결정
        if is_interrupted:
            response = interrupt_message
        else:
            response = final_recommendation
        
        return {
            "response": response,
            "followup_question": followup_question,
            "needs_human_input": needs_human_input,
            "product_ids": product_ids,
            "is_interrupted": is_interrupted
        }
    
    @classmethod
    def cleanup(cls):
        """
        애플리케이션 종료 시 자원을 정리합니다.
        """
        if cls._pool is not None:
            cls._pool.close()
            print("PostgreSQL connection pool closed.")