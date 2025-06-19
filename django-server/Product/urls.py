from django.urls import path
from . import views

urlpatterns = [
    path('details/<int:product_id>/', views.get_product_details, name='product_details'),
    path('details/', views.get_product_details, name='product_details_bulk'),
    path('get_weighted_scores/', views.get_weighted_scores, name='get_weighted_scores'),
    path('get_popular_products/', views.get_popular_products, name='get_popular_products'),
    path('get_best_selling_products/', views.get_best_selling_products, name='get_best_selling_products'),
] 