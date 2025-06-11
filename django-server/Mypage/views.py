from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Like
from Product.models import Products

# Create your views here.

@csrf_exempt
@require_http_methods(["POST", "DELETE", "GET"])
def like_api(request):
    """
    좋아요 API 엔드포인트
    POST: 좋아요 추가
    DELETE: 좋아요 제거
    GET: 좋아요 상태 확인
    """
    # 임시 사용자 ID (실제 구현에서는 인증된 사용자 정보 사용)
    user_id = 1
    
    if request.method == "GET":
        # 쿼리 파라미터에서 product_id 가져오기
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({"error": "상품 ID가 필요합니다."}, status=400)
        
        product = get_object_or_404(Products, id=product_id)
        is_liked = Like.objects.filter(user_id=user_id, product=product).exists()
        
        return JsonResponse({
            "is_liked": is_liked
        })
        
    elif request.method in ["POST", "DELETE"]:
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            if not product_id:
                return JsonResponse({"error": "상품 ID가 필요합니다."}, status=400)
            
            product = get_object_or_404(Products, id=product_id)
            
            if request.method == "POST":
                # 좋아요 추가 (이미 있으면 무시)
                like, created = Like.objects.get_or_create(
                    user_id=user_id,
                    product=product
                )
                return JsonResponse({
                    "message": "좋아요가 추가되었습니다." if created else "이미 좋아요가 되어있습니다.",
                    "is_liked": True
                })
                
            elif request.method == "DELETE":
                # 좋아요 제거
                like = Like.objects.filter(user_id=user_id, product=product)
                if like.exists():
                    like.delete()
                    return JsonResponse({
                        "message": "좋아요가 제거되었습니다.",
                        "is_liked": False
                    })
                else:
                    return JsonResponse({
                        "message": "좋아요가 되어있지 않습니다.",
                        "is_liked": False
                    })
                    
        except json.JSONDecodeError:
            return JsonResponse({"error": "잘못된 JSON 형식입니다."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "지원하지 않는 메서드입니다."}, status=405)
