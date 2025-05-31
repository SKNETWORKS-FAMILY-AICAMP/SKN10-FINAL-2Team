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

class SupplementRecommendationAgent:
    """
    영양제 추천 Agent 시스템을 관리하는 클래스.
    LangGraph 워크플로우를 캡슐화하고, 애플리케이션 생명주기 동안
    한 번만 초기화되도록 합니다.
    """
    _workflow = None  # 워크플로우 인스턴스를 저장할 클래스 변수

    @classmethod
    def create_supplement_recommendation_workflow(cls):
        """
        영양제 추천 시스템의 전체 워크플로우를 생성하고 컴파일합니다.
        이 메서드는 워크플로우가 아직 초기화되지 않았을 때만 실행됩니다.
        """
        if cls._workflow is None:
            # StateGraph 생성
            workflow = StateGraph(AgentState)

            # 노드 추가
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

            # 워크플로우 컴파일 및 클래스 변수에 저장
            cls._workflow = workflow.compile()
            print("LangGraph workflow compiled and initialized.")
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