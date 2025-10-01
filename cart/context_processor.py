from decimal import Decimal
from django.utils import timezone
from offers.models import Coupon
from .models import CartItems

def cart_context(request):
    total_price = Decimal("0.00")
    discount = Decimal("0.00")
    applied_coupon = None

    if request.user.is_authenticated:
        cart_items = CartItems.objects.filter(user=request.user).select_related('product', 'variant')
        for item in cart_items:
            item.item_total = Decimal(item.variant.price) * item.quantity
            total_price += item.item_total

        # Check if coupon exists in session
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
                    discount = min(discount, total_price)  # Ensure discount doesn't exceed total
                    applied_coupon = coupon
            except Coupon.DoesNotExist:
                # Optionally clear invalid coupon from session
                if "coupon_id" in request.session:
                    del request.session["coupon_id"]

    final_total = total_price - discount

    return {
        'cart_items': cart_items if request.user.is_authenticated else [],
        'total_price': total_price,
        'discount': discount,
        'final_total': final_total,
        'applied_coupon': applied_coupon,
    }