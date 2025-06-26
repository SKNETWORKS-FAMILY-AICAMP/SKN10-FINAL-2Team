from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from Chatbot.agent_system.agent import SupplementRecommendationAgent # Agent 클래스 임포트
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from Mypage.models import SurveyResponse
import json
from .models import ChatRooms, ChatMessages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from datetime import date
from django.core.cache import cache  # 캐시 임포트


class ChatWithNutiAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        # GET 요청 시 HTML 템플릿 렌더링
        return render(request, 'Chatbot/ChatNuti.html')
        
    def post(self, request, *args, **kwargs):
        try:
            # 채팅방 관리
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

            # 답변 대기 중인지 확인 (캐시)
            cache_key = f"chatbot_waiting_{chat_room_id}"
            if cache.get(cache_key):
                return Response({"error": "이전 답변이 완료될 때까지 기다려주세요."}, status=429)
            # 답변 대기 상태로 설정
            cache.set(cache_key, True, timeout=60)

            # 사용자 메시지 저장
            ChatMessages.objects.create(
                chat_room=chat_room,
                sender_type='user',
                message=user_query
            )
            
            # 가장 최신 SurveyResponse를 가져오도록 변경
            latest_survey = SurveyResponse.objects.filter(user_id=user.id).order_by('-created_at').first()
            user_health_info = latest_survey.responses if latest_survey else {}
            print("가져온 설문 조사 정보:", user_health_info)
            user_health_info["user_name"] = user.name
            user_health_info["user_age"] = None
            if user.birth_date:
                today = date.today()
                age = today.year - user.birth_date.year - ((today.month, today.day) < (user.birth_date.month, user.birth_date.day))
                user_health_info["user_age"] = age
            print("수정한 설문 조사 정보:", user_health_info)
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

            # 답변 완료 후 대기 상태 해제
            cache.delete(cache_key)

            # 응답 반환
            return Response({
                "final_recommendation": ai_response,
                "product_ids": product_ids,
                "chat_room_id": chat_room_id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # 예외 발생 시에도 대기 상태 해제
            if 'chat_room_id' in locals():
                cache_key = f"chatbot_waiting_{chat_room_id}"
                cache.delete(cache_key)
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_rooms(request):
    rooms = ChatRooms.objects.filter(user=request.user).order_by('-created_at')
    

    return JsonResponse([{
        'id': room.id,
        'title': room.title,
        'created_at': room.created_at.isoformat()
    } for room in rooms], safe=False)

def get_chat_messages(request, room_id):
    try:
        messages = ChatMessages.objects.filter(chat_room_id=room_id).order_by('created_at', 'id')
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