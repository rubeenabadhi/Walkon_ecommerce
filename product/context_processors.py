from .views import *


def user_product_list(request):
    products = (Product.objects
                .all()
                .prefetch_related('variants__images')  # Pre-fetch variants and images
                .select_related('category', 'brand', 'gender'))
    return {'products': products}