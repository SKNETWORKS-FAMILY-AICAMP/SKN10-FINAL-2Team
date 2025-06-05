from django.contrib import admin
from .models import Products, Review, Favorite

@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ('title', 'brand', 'total_price', 'average_rating')
    search_fields = ('title', 'brand')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'stars', 'sentiment', 'date')
    list_filter = ('sentiment', 'stars')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('user', 'created_at') 