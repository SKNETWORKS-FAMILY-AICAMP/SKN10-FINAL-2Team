from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def mypage_view(request):
    """마이페이지를 렌더링합니다."""
    context = {
        'user': request.user
    }
    return render(request, 'mypage/mypage.html', context) 