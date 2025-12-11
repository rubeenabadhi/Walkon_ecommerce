from django.core.paginator import Paginator
from .models import Gender, Product
from wishlist.models import WishlistItem
from .forms import ProductFilterForm

def user_product_list(request):
    products = Product.objects.all()
    filter_form = ProductFilterForm(request.GET or None)
    genders = Gender.objects.all()
    
    if filter_form.is_valid():
        category = filter_form.cleaned_data.get("category")
        brand = filter_form.cleaned_data.get("brand")
        gender = filter_form.cleaned_data.get("gender")
        min_price = filter_form.cleaned_data.get("min_price")
        max_price = filter_form.cleaned_data.get("max_price")
        sort_by = filter_form.cleaned_data.get("sort_by")

        if category:
            products = products.filter(category=category)
        if brand:
            products = products.filter(brand=brand)
        if gender:
            products = products.filter(gender=gender)
        if min_price:
            products = products.filter(variants__price__gte=min_price)
        if max_price:
            products = products.filter(variants__price__lte=max_price)

        if sort_by == "price_low":
            products = products.order_by("variants__price")
        elif sort_by == "price_high":
            products = products.order_by("-variants__price")
        elif sort_by == "latest":
            products = products.order_by("-created_at")
        elif sort_by == "popular":
            products = products.order_by("-views")

    # ✅ Ensure default ordering if none applied
    if not products.query.order_by:
        products = products.order_by("-created_at")  # newest first by default

    products = products.distinct()

    # ✅ Provide wishlist IDs globally
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).values_list("product_variant__product_id", flat=True)
        


    paginator = Paginator(products, 3)
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)

    return {
        "products": products,
        "filter_form": filter_form,
        "genders": genders,
        "wishlist_ids": wishlist_ids,
    }
