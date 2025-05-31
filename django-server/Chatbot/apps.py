from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Chatbot'

    # Agent 시스템 초기화를 위한 클래스 변수
    agent_workflow = None

    def ready(self):
        """
        장고 앱이 로드될 때 호출됩니다.
        여기서 Agent 워크플로우를 초기화합니다.
        """
        from Chatbot.agent_system.agent import SupplementRecommendationAgent
        print("Initializing Agent System...")
        # 클래스 메서드를 호출하여 워크플로우 초기화 (또는 이미 초기화되어 있다면 가져옴)
        ChatbotConfig.agent_workflow = SupplementRecommendationAgent.get_workflow()
        print("Agent System Initialized.")