from decimal import Decimal
from django.utils import timezone
from offers.models import Coupon
from .models import CartItems
from wishlist.models import WishlistItem

def cart_context(request):
    total_price = Decimal("0.00")
    discount = Decimal("0.00")
    applied_coupon = None
    cart_count = 0
    count_wishlist = 0
    cart_items = []

    if request.user.is_authenticated:
        cart_items = CartItems.objects.filter(
            user=request.user
        ).select_related('product', 'variant')

        cart_count = cart_items.count()
        count_wishlist = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).count()

        for item in cart_items:
            price = Decimal(item.variant.get_offer_price())
            item.item_total = price * item.quantity
            total_price += item.item_total

        # Coupon logic (unchanged)
        coupon_id = request.session.get("coupon_id")
        if coupon_id:
            try:
                coupon = Coupon.objects.get(id=coupon_id, active=True)
                now = timezone.now()
                if coupon.valid_from <= now <= coupon.valid_to:
                    if coupon.discount_type == "percentage":
                        discount = total_price * (Decimal(coupon.discount_value) / 100)
                    else:
                        discount = Decimal(coupon.discount_value)
                    discount = min(discount, total_price)
                    applied_coupon = coupon
            except Coupon.DoesNotExist:
                request.session.pop("coupon_id", None)

    final_total = total_price - discount

    return {
        'cart_items': cart_items,
        'total_price': total_price,
        'discount': discount,
        'final_total': final_total,
        'applied_coupon': applied_coupon,
        'cart_count': cart_count,
        'count_wishlist': count_wishlist
    }
