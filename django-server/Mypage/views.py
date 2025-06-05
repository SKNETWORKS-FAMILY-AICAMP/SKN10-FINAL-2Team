from django.shortcuts import render

def mypage_view(request):
    """마이페이지를 렌더링합니다."""
    return render(request, 'survey/mypage.html') 