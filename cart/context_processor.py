from .views import cart
from .models import CartItems

def cart_context(request):
    if request.user.is_authenticated:
        cart_items = CartItems.objects.filter(user=request.user).select_related('product', 'variant')
        total_price = 0
        for item in cart_items:
            item.item_total = item.variant.price * item.quantity  
            total_price += item.item_total
    else:
        cart_items = []
        total_price = 0

    return {
        'cart_items': cart_items,
        'total_price': total_price
    }
