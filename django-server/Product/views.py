from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from .models import Products
from django.http import JsonResponse
from Mypage.models import Like
import json
from django.http import JsonResponse
from Chatbot.models import NutritionDailyRec
from datetime import date

def get_age_from_birthdate(birth_date):
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def get_age_range(age):
    # NutritionDailyRec의 age_range와 매칭
    # 예: 6~8, 9~11, 12~14, 15~18, 19~29, 30~49, 50~64, 65~74, 75 이상
    ranges = [
        (6, 8, "6~8"), (9, 11, "9~11"), (12, 14, "12~14"), (15, 18, "15~18"),
        (19, 29, "19~29"), (30, 49, "30~49"), (50, 64, "50~64"), (65, 74, "65~74"), (75, 200, "75 이상")
    ]
    for start, end, label in ranges:
        if start <= age <= end:
            return label
    return None

def get_product_details(request, product_id=None):
    """
    단일 상품 또는 여러 상품의 상세 정보를 반환하는 API
    
    GET /product/details/{product_id}/ - 단일 상품 정보 반환
    GET /product/details/?ids=1,2,3 - 여러 상품 정보 반환
    """
    try:
        user = request.user
        user_id = user.id if user.is_authenticated else None
        # 사용자 정보 가져오기
        user_gender = None
        user_age = None
        user_age_range = None
        if user_id and hasattr(user, 'gender') and hasattr(user, 'birth_date') and user.birth_date:
            user_gender = user.gender
            user_age = get_age_from_birthdate(user.birth_date)
            user_age_range = get_age_range(user_age)
            # NutritionDailyRec의 성별은 '남자', '여자'로 저장됨
            if user_gender == 'male':
                user_gender_kor = '남자'
            elif user_gender == 'female':
                user_gender_kor = '여자'
            else:
                user_gender_kor = '남자'  # 기본값
        else:
            user_gender_kor = '남자'  # 기본값
            user_age_range = '19~29'  # 기본값
        if product_id:
            product = get_object_or_404(Products, id=product_id)
            is_liked = Like.objects.filter(user_id=user_id, product=product).exists() if user_id else False
            # 성분 정보 파싱 및 권장량 매칭
            try:
                ingredients_str = product.ingredients.replace("'", '"') if product.ingredients else '[]'
                ingredients = json.loads(ingredients_str)
            except Exception:
                ingredients = []
            print("ingredients:", ingredients)
            ingredients_with_rec = []
            for ing in ingredients:
                name = ing.get('ingredient_name')
                amount = ing.get('amount')
                unit = ing.get('unit')
                daily_rec = None
                percent = None
                if user_gender_kor and user_age_range and name:
                    rec = NutritionDailyRec.objects.filter(sex=user_gender_kor, age_range=user_age_range, nutrient=name).first()
                    if rec:
                        daily_rec = rec.daily
                        try:
                            percent = round((float(amount) / float(daily_rec)) * 100, 1) if daily_rec else None
                        except Exception:
                            percent = None
                ingredients_with_rec.append({
                    'ingredient_name': name,
                    'amount': amount,
                    'unit': unit,
                    'daily_rec': daily_rec,
                    'percent': percent
                })
            product_data = {
                'id': product.id,
                'url': product.url,
                'title': product.title,
                'safety_info': product.safety_info,
                'ingredients': ingredients_with_rec,  # 리스트로 반환
                'directions': product.directions,
                'brand': product.brand,
                'flavor': product.flavor,
                'supplement_type': product.supplement_type,
                'quantity': product.quantity,
                'product_form': product.product_form,
                'average_rating': product.average_rating,
                'total_reviews': product.total_reviews,
                'image_link': product.image_link,
                'total_price': product.total_price,
                'price_value': product.price_value,
                'vegan': product.vegan,
                'country_of_origin': product.country_of_origin,
                'is_liked': is_liked,
            }
            return JsonResponse(product_data)
        else:
            # 여러 상품 조회 (ids 쿼리 파라미터 사용)
            product_ids = request.GET.get('ids', '')
            if not product_ids:
                return JsonResponse({'error': '상품 ID가 제공되지 않았습니다.'}, status=400)
            
            # 쉼표로 구분된 ID 목록을 리스트로 변환
            id_list = [int(pid.strip()) for pid in product_ids.split(',') if pid.strip().isdigit()]
            
            if not id_list:
                return JsonResponse({'error': '유효한 상품 ID가 없습니다.'}, status=400)
            
            # 요청된 ID에 해당하는 상품들 조회
            products = Products.objects.filter(id__in=id_list)
            
            # 임시 사용자 ID (실제 구현에서는 인증된 사용자 정보 사용)
            user = request.user
            user_id = user.id
            
            # 좋아요한 상품 ID 목록 가져오기
            liked_product_ids = Like.objects.filter(user_id=user_id).values_list('product_id', flat=True)
            
            # 상품 목록에 좋아요 정보 추가
            for product in products:
                product.is_liked = product.id in liked_product_ids
            
            # 결과 포맷팅
            products_data = []
            for product in products:
                products_data.append({
                    'id': product.id,
                    'url': product.url,
                    'title': product.title,
                    'safety_info': product.safety_info,
                    'ingredients': product.ingredients,
                    'directions': product.directions,
                    'brand': product.brand,
                    'flavor': product.flavor,
                    'supplement_type': product.supplement_type,
                    'quantity': product.quantity,
                    'product_form': product.product_form,
                    'average_rating': product.average_rating,
                    'total_reviews': product.total_reviews,
                    'image_link': product.image_link,
                    'total_price': product.total_price,
                    'price_value': product.price_value,
                    'vegan': product.vegan,
                    'country_of_origin': product.country_of_origin,
                    'is_liked': product.is_liked,
                })
            # 요청한 id_list 순서대로 정렬
            id_to_product = {p['id']: p for p in products_data}
            ordered_products_data = [id_to_product[pid] for pid in id_list if pid in id_to_product]
            return JsonResponse({'products': ordered_products_data})
    
    except Products.DoesNotExist:
        return JsonResponse({'error': f'상품 ID {product_id}를 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'오류가 발생했습니다: {str(e)}'}, status=500)

class ProductDetailsAPIView(APIView):
    """
    상품 상세 정보를 반환하는 API 클래스 뷰
    """
    def get(self, request, product_id=None):
        return get_product_details(request, product_id)

def product_list(request):
    """
    상품 목록 페이지 뷰
    """
    products = Products.objects.all().order_by('-average_rating')
    
    # 임시 사용자 ID (실제 구현에서는 인증된 사용자 정보 사용)
    user_id = 1
    
    # 좋아요한 상품 ID 목록 가져오기
    liked_product_ids = Like.objects.filter(user_id=user_id).values_list('product_id', flat=True)
    
    # 상품 목록에 좋아요 정보 추가
    for product in products:
        product.is_liked = product.id in liked_product_ids
    
    context = {
        'products': products
    }
    
    return render(request, 'Product/product_list.html', context)



def get_weighted_scores(request):
    products = Products.objects.order_by('sales_ranks')[:10]
    print(products)
    return JsonResponse({'results': products})


def get_popular_products(request):
    products = Products.objects.order_by('-average_rating')[:10]
    print(products)
    return JsonResponse({'products': products})


def get_best_selling_products(request):
    products = Products.objects.order_by('sales_ranks')[:10]

    data = [
        {
            'id': p.id,
            'title': p.title,
            'url': p.url,
            'image_link': p.image_link or 'https://via.placeholder.com/150',
            'average_rating': p.average_rating,
            'price_value': p.price_value,
            'sales_ranks': p.sales_ranks,
        }
        for p in products
    ]

    return JsonResponse({'results': data})