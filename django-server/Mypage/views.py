from django.shortcuts import render
from .models import Like
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

# @login_required
def like_list(request):
    User = get_user_model()
    user = User.objects.get(pk=1)
    # user = request.user
    like_list = Like.objects.filter(user=user).select_related('product')
    return render(request, 'Mypage/like.html', {'user': user, 'like_list': like_list})

@require_POST
# @login_required
def like_delete(request):
    product_id = request.POST.get('product_id')
    User = get_user_model()
    user = User.objects.get(pk=1)  # 실제 서비스에서는 request.user 사용
    # user = request.user
    try:
        like = Like.objects.get(user=user, product_id=product_id)
        like.delete()
        return JsonResponse({'success': True})
    except Like.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)

@require_POST
# @login_required
def like_add(request):
    product_id = request.POST.get('product_id')
    User = get_user_model()
    user = User.objects.get(pk=1)  # 실제 서비스에서는 request.user 사용
    # user = request.user
    try:
        Like.objects.get_or_create(user=user, product_id=product_id)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
