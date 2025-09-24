from .views import cart
from .models import CartItems
from decimal import Decimal

def cart_context(request):
    total_price = Decimal("0.00")

    if request.user.is_authenticated:
        cart_items = CartItems.objects.filter(user=request.user).select_related('product', 'variant')
        for item in cart_items:
            item.item_total = Decimal(item.variant.price) * item.quantity
            total_price += item.item_total
    else:
        cart_items = []

    return {
        'cart_items': cart_items,
        'total_price': total_price
    }
