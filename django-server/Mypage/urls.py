from django.urls import path
from .views import like_list, like_delete, like_add, product_click

urlpatterns = [
    path('like/', like_list, name='like_list'),
    path('like/delete/', like_delete, name='like_delete'),
    path('like/add/', like_add, name='like_add'),
    path('product/click/', product_click, name='product_click'),
]
