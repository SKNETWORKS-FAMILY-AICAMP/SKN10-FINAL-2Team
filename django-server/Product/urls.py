from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('like/', views.like_product, name='like_product'),
    path('analysis/', views.analysis, name='analysis'),
    path('analysis/view/', views.analysis_view, name='analysis_view'),
    path('like-product/view/', views.like_product_view, name='like_product_view'),
    path('analyze-image/', views.analyze_image_view, name='analyze_image'),
    path('analyze-ingredients/', views.analyze_ingredients_view, name='analyze_ingredients'),
    path('load-favorites/', views.load_favorites_view, name='load_favorites'),
    path('add_favorite/<int:product_id>/', views.add_favorite, name='add_favorite'),
    path('remove_favorite/<int:product_id>/', views.remove_favorite, name='remove_favorite'),
] 