from .models import Wishlist, WishlistItem

def wishlist_context(request):
    if request.user.is_authenticated:
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        wishlist_ids = WishlistItem.objects.filter(wishlist=wishlist).values_list("product_variant__product_id", flat=True)
        return {"wishlist_ids": list(wishlist_ids)}
    return {"wishlist_ids": []}
