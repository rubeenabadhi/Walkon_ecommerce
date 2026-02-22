from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from .models import *
from product.models import *
from wishlist.models import Wishlist
from django.db.models import Sum


# Create your views here.

def cart(request):
    if request.user.is_authenticated:
        cart_items = CartItems.objects.filter(user=request.user).select_related('product', 'variant')
        total_price = 0
        for item in cart_items:
            price = item.variant.get_offer_price()
            item.item_total = price * item.quantity 
            total_price += item.item_total
    else:
        return redirect('login')

    return render(request, 'user/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })



@login_required(login_url="login")
def add_to_cart(request, slug):
    print("Hit add_to_cart view with:", slug, request.POST.dict())

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method."})

    variant_id = request.POST.get("variant_id")
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Invalid quantity."})

    if not variant_id:
        return JsonResponse({"status": "error", "message": "Please select a size."})

    product = get_object_or_404(Product, slug=slug)
    variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    # Product-level availability check
    if not product.is_active:
        return JsonResponse({"status": "error", "message": "This product is not available."})

    product_stock = variant.stock or 0
    if product_stock <= 0:
        return JsonResponse({"status": "error", "message": "This product is out of stock."})

    # How much of this product the CURRENT user already has in cart
    existing_user_qty = CartItems.objects.filter(user=request.user, variant=variant).aggregate(total=Sum('quantity'))['total'] or 0

    # available for this user to add (product-level stock minus what user already has)
    available_for_user = product_stock - existing_user_qty
    if available_for_user <= 0:
        return JsonResponse({"status": "error", "message": "No stock available to add (you already reserved items in cart)."})

    if quantity > available_for_user:
        return JsonResponse({"status": "error", "message": f"Not enough stock available. Only {available_for_user} left (considering your cart)."} )

    max_allowed = min(available_for_user, 5)
    if quantity > max_allowed:
        return JsonResponse({"status": "error", "message": f"Cannot add more than {max_allowed} items."})

    # Add or update cart item
    cart_item, created = CartItems.objects.get_or_create(
        user=request.user,
        product=product,
        variant=variant,
        defaults={"quantity": quantity}
    )
    if not created:
        new_qty = cart_item.quantity + quantity
        if new_qty > min(available_for_user, 5):
            return JsonResponse({"status": "error", "message": f"Cannot exceed {min(available_for_user,5)} items in cart."})
        cart_item.quantity = new_qty
        cart_item.save()
    else:
        print(" Added new item to cart.")

    # Remove from wishlist if exists
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist.items.filter(product_variant=variant).delete()
    except Exception:
        pass

    cart_count = CartItems.objects.filter(user=request.user).count()
    return JsonResponse({
        "status": "success",
        "message": f"{product.name} added to cart successfully!",
        "cart_count": cart_count,
    })

@login_required(login_url='login')
def update_cart(request, cart_item_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method."})

    action = request.POST.get("action")
    try:
        cart_item = CartItems.objects.get(id=cart_item_id, user=request.user)
    except CartItems.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Item not found."})

    deleted = False

    if action == "increment":
        max_quantity = min(cart_item.variant.stock, 5)
        if cart_item.quantity < max_quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            return JsonResponse({"status": "error", "message": f"Max {max_quantity} items allowed."})

    elif action == "decrement":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            deleted = True
    elif action == "remove":
        cart_item.delete()
        deleted = True

    else:
        return JsonResponse({"status": "error", "message": "Invalid action."})

    # Recalculate totals
    remaining_items = CartItems.objects.filter(user=request.user)
    total_price = sum(
        float(i.variant.get_offer_price() * i.quantity)
        for i in remaining_items
    )

    response_data = {
        "status": "success",
        "total_price": float(total_price),
        "cart_count": remaining_items.count(),
        "deleted": deleted,
    }

    if not deleted:
        response_data.update({
            "quantity": cart_item.quantity,
            "item_total": float(cart_item.variant.get_offer_price() * cart_item.quantity),
            "item_id": cart_item.id,  # just in case
        })

    return JsonResponse(response_data)


