from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.apps import apps # apps 모듈 임포트
from Chatbot.agent_system.nodes import AgentState # AgentState 임포트

class ChatWithNutiAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # GET 요청 시 HTML 템플릿 렌더링
        return render(request, 'Chatbot/ChatNuti.html')
        
    def post(self, request, *args, **kwargs):
        # 사용자로부터 받은 데이터를 AgentState의 초기값으로 설정
        health_template = {
            "기본 정보": {
                "이름": "홍승표",
                "성별": "남자",
                "생년": 1990,
                "몸무게": 70,
                "키": 175
            },
            "생활 습관": {
                "주로 앉아서 하는 일을 하시나요?": "예",
                "낮에 실내에 주로 계신가요?": "예",
                "규칙적으로 운동을 하시나요?": "아니오",
                "담배를 피우시나요?": "아니오",
                "일주일에 소주 2병 또는 맥주 8병을 초과하여 드시나요?": "아니오",
                "평상시에 피곤함을 많이 느끼시나요?": "예",
                "잠을 개운하게 푹 주무시나요?": "아니오",
                "충분한 수면(7~8시간) 잠을 자도 피곤한가요?": "예"
            },
            "현재 건강 상태": {
                "스트레스를 많이 받으시나요?": "예",
                "평상시에 설사나 변비를 자주 경험하시나요?": "아니오",
                "다음 중 해당하는 증상을 모두 골라주세요.": {
                    "땀이 잘 나지 않는 편입니다.": "아니오",
                    "일어날 때 어지러움을 자주 느낍니다.": "예",
                    "어두운 곳에서 사물 구별이 어렵습니다.": "예",
                    "소변이 자주 마려워서 생활이 불편합니다.": "아니오"
                },
                "식사 후 자주 경험하는 증상을 모두 선택하세요.": {
                    "배에 가스가 잘 찹니다.(복부팽만감, 방귀)": "예",
                    "트름이 잦고 소화가 잘 안되어 속이 두부룩한 느낌입니다.": "예"
                },
                "감기에 잘 걸리거나 입술 포진(물집)이 잘 생기시나요?": "예",
                "편도선이 자주 붓거나 눈병이 잘 생기시나요?": "아니오",
                "눈이 건조하거나 피로감을 자주 느끼시나요?": "예"
            },
            "건강 목표": {
                "피부보습에 도움이 되는 영양제를 추천해 드릴까요?": "예",
                "인지력과 기억력 개선에 도움되는 영양제를 추천해드릴까요?": "아니오",
                "체중 감량 계획이 있으신가요?": "아니오"
            },
            "기존 질환 및 약 복용": {
                "아래 중 알러지가 있어 전혀 못드시는 식품을 선택해 주세요.": [
                    "땅콩",
                    "밀"
                ],
                "드시고 계신 만성질환 약이 있으신가요?": [
                    "고혈압 약"
                ],
                "지난 1년간 항생제나 항바이러스제를 복용하신적이 한번이라도 있으신가요?": "예",
                "향후 2주 이내에 수술 계획이 있거나 지난 2주 이내에 수술받은 적이 있으신가요?": "아니오"
            }
        }
        
        # 클라이언트로부터 받은 user_query 사용
        user_query = request.data.get('user_query', '')
        if not user_query:
            return Response({"error": "사용자 쿼리가 제공되지 않았습니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        state: AgentState = {
            "user_query": user_query,  # 클라이언트로부터 받은 쿼리 사용
            "user_health_info": health_template.copy(),
            "extracted_info": {},
            "kag_query": "",
            "kag_results": [],
            "rerank_results": [],
            "final_results": [],
            "final_recommendation": ""
        }

        # 초기화된 Agent 워크플로우 가져오기
        # apps 모듈을 통해 ChatbotConfig 인스턴스에 접근
        chatbot_config = apps.get_app_config('Chatbot')
        agent_workflow = chatbot_config.agent_workflow

        if not agent_workflow:
            return Response(
                {"error": "Agent workflow not initialized. Please restart the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Agent 워크플로우 실행
            # LangGraph의 invoke 메서드 사용
            final_state = agent_workflow.invoke(state)

            # 최종 결과 반환
            return Response({
                "final_recommendation": final_state.get("final_recommendation"),
                "details": final_state # 디버깅을 위해 전체 상태 반환 가능
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"An error occurred during agent execution: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )