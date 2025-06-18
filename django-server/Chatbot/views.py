from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.apps import apps # apps 모듈 임포트
from Chatbot.agent_system.state import AgentState # AgentState 임포트 경로 수정
from Chatbot.agent_system.agent import SupplementRecommendationAgent # Agent 클래스 임포트
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from Account.models import CustomUser
import json
from .models import ChatRooms, ChatMessages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from langchain_core.messages import HumanMessage

@permission_classes([IsAuthenticated])
class ChatWithNutiAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # GET 요청 시 HTML 템플릿 렌더링
        return render(request, 'Chatbot/ChatNuti.html')
        
    def post(self, request, *args, **kwargs):
        try:
            # 채팅방 관리
            #user_id = request.data.get('user_id', 1)  # 임시로 user_id 1 사용
            chat_room_id = request.data.get('chat_room_id')
            user_query = request.data.get('user_query')

            if not user_query:
                return Response({"error": "사용자 쿼리가 제공되지 않았습니다."}, status=status.HTTP_400_BAD_REQUEST)

            # 사용자 정보 가져오기
            user = request.user

            # 새 채팅방 생성 또는 기존 채팅방 가져오기
            if not chat_room_id:
                chat_room = ChatRooms.objects.create(
                    user=user,
                    title=user_query[:30] + "..."
                )
                chat_room_id = chat_room.id
            else:
                chat_room = ChatRooms.objects.get(id=chat_room_id)

            # 사용자 메시지 저장
            ChatMessages.objects.create(
                chat_room=chat_room,
                sender_type='user',
                message=user_query
            )

            # 사용자 건강 정보 - 이 부분은 실제 사용자 데이터로 대체해야 함
            user_health_info = {
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

            # 랭그래프 에이전트를 사용하여 응답 생성
            # process_message 메서드를 사용하여 간소화
            result = SupplementRecommendationAgent.process_message(
                thread_id=str(chat_room_id),
                message=user_query,
                user_health_info=user_health_info,
                user_id=user.id
            )
            
            ai_response = result.get("response", "")
            followup_question = result.get("followup_question", "")
            product_ids = result.get("product_ids", "")

            # 추가 정보가 필요한 경우 처리
            if followup_question:
                ai_response = ai_response + "\n\n" + followup_question

            # AI 응답 저장
            ChatMessages.objects.create(
                chat_room=chat_room,
                sender_type='assistant',
                message=ai_response,
                product_ids=product_ids
            )

            # 응답 반환
            return Response({
                "final_recommendation": ai_response,
                "product_ids": product_ids,
                "chat_room_id": chat_room_id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_rooms(request):
    # Temporary: Get rooms for user_id 1
    rooms = ChatRooms.objects.filter(user=request.user).order_by('-created_at')
    

    return JsonResponse([{
        'id': room.id,
        'title': room.title,
        'created_at': room.created_at.isoformat()
    } for room in rooms], safe=False)

def get_chat_messages(request, room_id):
    try:
        messages = ChatMessages.objects.filter(chat_room_id=room_id).order_by('created_at')
        return JsonResponse([{
            'id': msg.id,
            'sender_type': msg.sender_type,
            'message': msg.message,
            'product_ids': msg.product_ids,
            'created_at': msg.created_at.isoformat()
        } for msg in messages], safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)})

@csrf_exempt
def update_chat_room(request, room_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_title = data.get('title')
            
            if not new_title:
                return JsonResponse({'success': False, 'error': '제목이 제공되지 않았습니다.'})
            
            chat_room = ChatRooms.objects.get(id=room_id)
            chat_room.title = new_title
            chat_room.save()
            
            return JsonResponse({'success': True})
        except ChatRooms.DoesNotExist:
            return JsonResponse({'success': False, 'error': '채팅방을 찾을 수 없습니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def delete_chat_room(request, room_id):
    if request.method == 'POST':
        try:
            chat_room = ChatRooms.objects.get(id=room_id)
            chat_room.delete()
            return JsonResponse({'success': True})
        except ChatRooms.DoesNotExist:
            return JsonResponse({'success': False, 'error': '채팅방을 찾을 수 없습니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})