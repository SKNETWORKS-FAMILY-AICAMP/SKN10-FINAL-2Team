from Chatbot.agent_system.nodes import (
    AgentState,
    extract_health_info,
    extract_comprehensive_info,
    build_kag_query,
    send_kag_query,
    rerank_agent,
    select_product,
    final_answer
)

# --------------------------
# 9. 워크플로우 연결 (LangGraph StateGraph)
# --------------------------
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, List, Any, Annotated, Optional
import json
import os
from dotenv import load_dotenv

# PostgreSQL 영속성 체크포인터 관련 모듈 추가
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

# 환경변수 로드
load_dotenv()

class SupplementRecommendationAgent:
    """
    영양제 추천 Agent 시스템을 관리하는 클래스.
    LangGraph 워크플로우를 캡슐화하고, 애플리케이션 생명주기 동안
    한 번만 초기화되도록 합니다.
    """
    _workflow = None  # 워크플로우 인스턴스를 저장할 클래스 변수
    _pool = None  # DB 커넥션 풀을 저장할 클래스 변수

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
    def create_supplement_recommendation_workflow(cls):
        """
        영양제 추천 시스템의 전체 워크플로우를 생성하고 컴파일합니다.
        이 메서드는 워크플로우가 아직 초기화되지 않았을 때만 실행됩니다.
        PostgreSQL 체크포인터를 사용하여 상태 영속성을 제공합니다.
        """
        if cls._workflow is None:
            # StateGraph 생성 - LangGraph에게 상태 관리를 위임
            workflow = StateGraph(AgentState)

            # 노드 추가 - 각 노드는 상태를 직접 수정하지 않고 변경사항만 반환
            workflow.add_node("extract_health_info", extract_health_info)
            workflow.add_node("extract_comprehensive_info", extract_comprehensive_info)
            workflow.add_node("build_kag_query", build_kag_query)
            workflow.add_node("send_kag_query", send_kag_query)
            workflow.add_node("rerank_agent", rerank_agent)
            workflow.add_node("select_product", select_product)
            workflow.add_node("final_answer", final_answer)

            # 엣지 연결 (순차적 실행 흐름)
            workflow.add_edge("extract_health_info", "extract_comprehensive_info")
            workflow.add_edge("extract_comprehensive_info", "build_kag_query")
            workflow.add_edge("build_kag_query", "send_kag_query")
            workflow.add_edge("send_kag_query", "rerank_agent")
            workflow.add_edge("rerank_agent", "select_product")
            workflow.add_edge("select_product", "final_answer")
            workflow.add_edge("final_answer", END)

            # 시작점 설정
            workflow.set_entry_point("extract_health_info")

            try:
                # PostgreSQL 체크포인터 설정
                pool = cls.get_db_connection_pool()
                checkpointer = PostgresSaver(pool)
                
                # 테이블 생성 등 필요한 초기 설정
                checkpointer.setup()
                print("PostgreSQL checkpointer setup completed.")
                
                # 워크플로우 컴파일 및 클래스 변수에 저장 (체크포인터 적용)
                cls._workflow = workflow.compile(checkpointer=checkpointer)
                print("LangGraph workflow compiled with PostgreSQL persistence.")
            except Exception as e:
                print(f"Failed to setup PostgreSQL checkpointer: {e}")
                # 체크포인터 없이 컴파일 (폴백)
                cls._workflow = workflow.compile()
                print("LangGraph workflow compiled without persistence (fallback mode).")
        else:
            print("LangGraph workflow already initialized.")
        return cls._workflow

    @classmethod
    def get_workflow(cls):
        """
        초기화된 LangGraph 워크플로우 인스턴스를 반환합니다.
        필요하다면 이 메서드를 통해 워크플로우를 초기화합니다.
        """
        if cls._workflow is None:
            cls.create_supplement_recommendation_workflow()
        return cls._workflow
    
    @classmethod
    def get_thread_config(cls, thread_id):
        """
        특정 스레드 ID에 대한 구성을 반환합니다.
        이를 통해 각 사용자(스레드)별로 상태를 분리하여 관리합니다.
        """
        return {"configurable": {"thread_id": str(thread_id)}}
    
    @classmethod
    def cleanup(cls):
        """
        애플리케이션 종료 시 자원을 정리합니다.
        """
        if cls._pool is not None:
            cls._pool.close()
            print("PostgreSQL connection pool closed.")