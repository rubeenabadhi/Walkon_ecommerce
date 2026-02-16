from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Wishlist, WishlistItem
from product.models import Product, ProductVariant
from cart.models import CartItems

# -------------------
# counter for wishlist,cart in navbar
def wishlist_cart_counts(request):
    if request.user.is_authenticated:
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        count_wishlist = wishlist.items.count()
        cart_count = CartItems.objects.filter(user=request.user).count()
        return {
            "count_wishlist": count_wishlist,
            "cart_count": cart_count
        }
    return {
        "count_wishlist": 0,
        "cart_count": 0
    }
# Toggle Wishlist (Ajax)
# -------------------
@login_required
def toggle_wishlist(request, product_id):
    variant_id = request.POST.get("variant_id")
    if not variant_id:
        return JsonResponse({"status": "error", "message": "Variant required"}, status=400)

    try:
        variant = ProductVariant.objects.get(id=variant_id, product_id=product_id)
    except ProductVariant.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Product not found"}, status=404)

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

    item, created = WishlistItem.objects.get_or_create(
        wishlist=wishlist,
        product_variant=variant
    )
    
    if not created:
        item.delete()
        wishlist_count = wishlist.items.count()
        return JsonResponse({"status": "removed", "in_wishlist": False, "wishlist_count": wishlist_count})

    print(" Added to wishlist:", variant)  # Debug log
    wishlist_count= wishlist.items.count()
    return JsonResponse({"status": "added", "in_wishlist": True, "wishlist_count": wishlist_count})
# -------------------
# Wishlist Page
# -------------------
@login_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist_items = wishlist.items.select_related(
        "product_variant__product"
    ).prefetch_related(
        "product_variant__product__variants__size"
    )

    for item in wishlist_items:
        unique_sizes = {}
        for variant in item.product_variant.product.variants.all():
            size_label = variant.size.label
            if size_label not in unique_sizes:
                unique_sizes[size_label] = variant
        item.unique_sizes = unique_sizes.values()

    return render(request, "user/wishlist.html", {
        "wishlist_items": wishlist_items
    })

# -------------------
# Add specific variant to wishlist
# -------------------
@login_required
@require_POST
def add_to_wishlist(request, variant_id):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user) # Get or create wishlist for the user
    variant = get_object_or_404(ProductVariant, id=variant_id)
    WishlistItem.objects.get_or_create(wishlist=wishlist, product_variant=variant)
    return JsonResponse({"status": "added"})


# -------------------
# Remove specific variant from wishlist
# -------------------
@login_required('')
@require_POST
def remove_from_wishlist(request, item_id):
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    wishlist_item.delete()
    print(" Removed from wishlist:", wishlist_item)
    return JsonResponse({"status": "success"})
# -------------------
# Move from wishlist → cart
# -------------------
@login_required
@require_POST
def add_to_cart_from_wishlist(request, variant_id):
    #  Get selected variant directly
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product

    # Remove any wishlist item that matches this product for the user
    WishlistItem.objects.filter(
        wishlist__user=request.user,
        product_variant__product=product
    ).delete()

    #  Add to cart
    cart_item, created = CartItems.objects.get_or_create(
        user=request.user,
        product=product,
        variant=variant,
        defaults={"quantity": 1}
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    cart_count = CartItems.objects.filter(user=request.user).count()
    print(f" Moved {product.name} (Size {variant.size.label}) to cart.")
    return JsonResponse({
        "status": "success",
        "message": f" {product.name} (Size {variant.size.label}) added to cart successfully!",
        "cart_count": cart_count
    })
