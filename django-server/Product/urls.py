from django.urls import path
from . import views

urlpatterns = [
    path('details/<int:product_id>/', views.get_product_details, name='product_details'),
    path('details/', views.get_product_details, name='product_details_bulk'),
] 