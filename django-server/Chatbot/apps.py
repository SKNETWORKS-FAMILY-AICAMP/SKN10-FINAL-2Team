from django.apps import AppConfig
import atexit
import signal
import sys


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Chatbot'

    # 더 이상 agent_workflow 클래스 변수가 필요하지 않음
    # LangGraph에서 SupplementRecommendationAgent가 상태를 자체적으로 관리

    def ready(self):
        """
        장고 앱이 로드될 때 호출됩니다.
        여기서 Agent 워크플로우를 초기화합니다.
        """
        # 앱이 리로드되는 경우는 제외
        if 'runserver' not in sys.argv:
            return

        from Chatbot.agent_system.agent import SupplementRecommendationAgent
        print("Initializing LangGraph Agent System with PostgreSQL persistence...")
        
        # 클래스 메서드를 호출하여 워크플로우 초기화
        # 각 노드는 상태를 직접 변경하지 않고, LangGraph가 상태 관리를 담당
        SupplementRecommendationAgent.create_supplement_recommendation_workflow()
        print("LangGraph Agent System Initialized.")
        
        # 앱 종료 시 자원 정리를 위한 핸들러 등록
        def cleanup_resources():
            print("Cleaning up LangGraph resources...")
            SupplementRecommendationAgent.cleanup()
            print("Cleanup complete.")
        
        # 프로세스 종료 시 호출될 함수 등록
        atexit.register(cleanup_resources)
        
        # 시그널 핸들러 등록 (키보드 인터럽트 등)
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, lambda s, f: (cleanup_resources(), sys.exit(0)))