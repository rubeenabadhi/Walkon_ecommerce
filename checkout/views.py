from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from address.models import Address
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from cart.models import CartItems
from order.models import Order, OrderItem
from django.db import transaction
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Payment
from decimal import Decimal


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))



# Create your views here.
 #===========================================select address view =================================
@login_required(login_url="login")
def select_address(request):
    addresses = Address.objects.filter(user=request.user)
    if request.method == "POST":
        selected_address_id = request.POST.get("selected_address")
        
        if selected_address_id:
            selected_address = get_object_or_404(Address, id=selected_address_id, user=request.user)
            request.session['selected_address_id'] = selected_address.id
            print("Selected Address ", selected_address.full_name,selected_address.city)  # Debugging line
            messages.success(request, "Address selected successfully.")
            return redirect("select_payment")  # Redirect to payment page after selecting address
        else:
            print("No address selected.")
            messages.error(request, "Please select an address.")
            return redirect("select_address")
    return render(request, "user/select_address.html", {"addresses": addresses})

# =======================================add address view checkout page=========================
@login_required(login_url="login")
def add_address_checkout(request):
    if request.method == "POST":
        Address.objects.create(
            user=request.user,
            full_name=request.POST['full_name'],
            phone_number=request.POST['phone'],
            address=request.POST['address'],
            street=request.POST['street'],
            district=request.POST['district'],
            city=request.POST['city'],
            state=request.POST['state'],
            country=request.POST['country'],
            pincode=request.POST['pincode'],
        )
        print("Address added successfully for user:", request.user)
        messages.success(request, "Address added successfully.")
        return HttpResponseRedirect(reverse("select_address"))
    
#=======================================edit address view checkout page ==========================
@login_required(login_url="login")
def edit_address_checkout(request, address_id):
    print("Editing Address ID:", address_id, request.user) # Debugging line
    if request.method == "POST":
        address = get_object_or_404(Address, id=address_id, user=request.user)
        print("Editing Address ID:", address.user)  # Debugging line
        if not address:
            messages.error(request, "Address not found.")
            return redirect("select_address")

        # Update fields
        address.full_name = request.POST.get("full_name")
        address.phone_number = request.POST.get("phone")
        address.street = request.POST.get("street")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.district = request.POST.get("district")
        address.address = request.POST.get("address")
        address.pincode = request.POST.get("pincode")
        address.country = request.POST.get("country")

        if (
            not address.full_name or
            not address.phone_number or
            not address.address or
            not address.city or
            not address.district or
            not address.state or
            not address.country or
            not address.pincode
        ):
            messages.error(request, "Please fill all the fields.")
            return redirect("edit_address", address_id=address_id)

        print("Address updated successfully.", address.full_name, address.street) 
        address.save() 
        messages.success(request, "Address updated successfully ")
        return redirect("select_address")
    
    return redirect("select_address")  # Always redirect to checkout

#======================================selecr payment method view =========================
@login_required(login_url="login")
def select_payment(request):
    cart_items = CartItems.objects.filter(user=request.user)
    if not cart_items.exists():
        messages.error(request, "Your cart is empty!")
        return redirect("cart:cart")

    address_id = request.session.get("selected_address_id")
    if not address_id:
        messages.error(request, "Please select an address.")
        return redirect("select_address")
    address = Address.objects.get(id=address_id, user=request.user)

    total_price = sum(item.variant.price * item.quantity for item in cart_items)

    # Check if there is already a pending order
    order = Order.objects.filter(user=request.user, status="pending").last()
    
    # If no pending order, create one
    if not order:
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method="razorpay",  # default, can update later
                total_amount=total_price,
                status="pending",
            )
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_variant=item.variant,
                    quantity=item.quantity,
                    price=item.variant.price,
                )

    # Render template and pass order
    return render(request, "user/select_payment.html", {
        "cart_items": cart_items,
        "total_price": total_price,
        "order": order,  # ✅ ensures order.id exists
    })
#==================== RAZORPAY INTEGRATION ===============================


@csrf_exempt
@login_required(login_url="login")
def create_razorpay_order(request, order_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Calculate cart total
    cart_items = CartItems.objects.filter(user=request.user).select_related('variant')
    total_amount = Decimal("0.00")
    for item in cart_items:
        total_amount += Decimal(item.variant.price) * item.quantity

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    razorpay_order = client.order.create({
        "amount": int(total_amount * 100),  # in paise
        "currency": "INR",
        "receipt": str(order.id),
        "payment_capture": 1
    })

    # Check if Payment already exists, create if not
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "payment_method": "razorpay",
            "payment_status": "pending",
            "paid_amount": total_amount,
            "payment_gateway": "Razorpay",
            "gateway_order_id": razorpay_order["id"]
        }
    )

    if not created:
        payment.payment_status = "pending"
        payment.paid_amount = total_amount
        payment.payment_gateway = "Razorpay"
        payment.gateway_order_id = razorpay_order["id"]
        payment.save()

    print(f"Payment created/updated: ID={payment.id}, gateway_order_id={payment.gateway_order_id},total_amount={total_amount}")

    return JsonResponse({
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": float(total_amount),
        "currency": "INR",
    })# Verify Razorpay payment
@csrf_exempt
@login_required(login_url="login")
def verify_razorpay_payment(request):
    print("Payment verification started...")
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)

    payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    signature = request.POST.get("razorpay_signature")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
        print("Payment verified successfully.")

        # Query Payment using gateway_order_id
        payment = get_object_or_404(Payment, gateway_order_id=razorpay_order_id)
        print("Payment record found:", payment.id,"paymnent_gateway_order_id:",payment.gateway_order_id)
        
        # Start transaction to ensure atomicity
        with transaction.atomic():
            # Update Payment
            payment.payment_status = "success"
            payment.gateway_payment_id = payment_id
            payment.gateway_signature = signature
            payment.paid_at = timezone.now()
            payment.save()
            print("Payment record updated:", payment.id)

            # Update related Order
            order = payment.order
            order.status = "confirmed"
            order.payment_method = "razorpay"
            order.save()
            print("Order status updated:", order.id, "User:", order.user.id)

            # Get cart items for the user
            cart_items = CartItems.objects.filter(user=request.user)
            if not cart_items.exists():
                print("No cart items found for user during payment verification.")
            else:
                # Move cart items to Order Items and decrease stock
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product_variant=item.variant,
                        quantity=item.quantity,
                        price=item.variant.price,
                    )
                    print(f"Before stock: {item.variant.product.stock}, Ordered: {item.quantity}")
                    item.variant.product.stock -= item.quantity
                    item.variant.product.save()
                    print(f"After stock: {item.variant.product.stock}")

                # Clear cart items
                cart_items.delete()
                print("Cart items cleared for user:", request.user.id)

        return JsonResponse({"status": "success", "order_id": str(order.id)})

    except razorpay.errors.SignatureVerificationError as e:
        print("Payment verification failed:", str(e))
        return JsonResponse({"status": "failed", "message": "Payment verification failed"}, status=400)
    except Exception as e:
        print("Verification error:", str(e))
        return JsonResponse({"status": "failed", "message": str(e)}, status=400)    
#==================== PLACE ORDER VIEW ===============================
@login_required(login_url="login")
def place_order(request):
    cart_items = CartItems.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.error(request, "Your cart is empty!")
        print("Cart is empty during order placement.")
        return redirect("cart:cart")  # Redirect to cart if empty

    # Get selected address from session
    address_id = request.session.get("selected_address_id")
    if not address_id:
        messages.error(request, "Please select an address.")
        return redirect("select_address")
    address = Address.objects.get(id=address_id, user=request.user)

    # Get payment method from POST (from merged form)
    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        if not payment_method:
            messages.error(request, "Please select a payment method.")
            return redirect("select_payment")
        request.session["payment_method"] = payment_method  # optional

    else:
        messages.error(request, "Invalid request.")
        return redirect("select_payment")

    total_price = sum(item.variant.price * item.quantity for item in cart_items)

    try:
        with transaction.atomic():  # rollback if any error means order not created in DB

            # Create Order
            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method=payment_method,
                total_amount=total_price,
                status="pending",
            )

            # Move cart items → Order Items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_variant=item.variant,
                    quantity=item.quantity,
                    price=item.variant.price,
                )

                # Decrease stock
                print(f"Before stock: {item.product.stock}, Ordered: {item.quantity}")
                item.product.stock -= item.quantity
                item.product.save()
                print(f"After stock: {item.product.stock}")

            # Clear Cart
            cart_items.delete()

            # Clear session
            request.session.pop("selected_address_id", None)
            request.session.pop("payment_method", None)

        return redirect("order_success", order_id=order.order_id)  # Thank you page

    except Exception as e:
        messages.error(request, f"Order failed: {e}")
        print("Order placement error:", e)
        return redirect("select_payment")

#==================== ORDER SUCCESS VIEW ===============================


@login_required(login_url="login")
def order_success(request, order_id):
    print(f"Order success for order_id: {order_id}")
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'user/order_success.html', {'order': order})