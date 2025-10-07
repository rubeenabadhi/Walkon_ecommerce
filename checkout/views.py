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
from django.db.models import F
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Payment
from decimal import Decimal
from offers.models import Coupon, UserCoupon
from wallet.models import Wallet, WalletTransaction
import json



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

    # wallet integration
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    wallet_balance = wallet.balance  # actual balance
    
    # Use session final_total if exists (after coupon), else total_price
    final_total = request.session.get("final_total")
    if final_total is None:
        final_total = Decimal(total_price)

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
        "wallet_balance": wallet_balance,
        "final_total": final_total
    })

# ==================== WALLET PAYMENT VIEW ===============================
@login_required(login_url="login")
def wallet_payment(request, order_id):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("select_payment")

    user = request.user
    wallet = get_object_or_404(Wallet, user=user)
    order = get_object_or_404(Order, id=order_id, user=user)

    # Get amount (final total)
    final_total = request.session.get("final_total")
    if final_total is None:
        cart_items = CartItems.objects.filter(user=request.user).select_related('variant')
        final_total = sum(Decimal(item.variant.price) * item.quantity for item in cart_items)

    final_total = Decimal(str(final_total)).quantize(Decimal('0.01'))
    print("Wallet Payment Initiated: User:", user.username, "Order:", order.order_id, "Amount:", final_total)
    if wallet.balance < Decimal(final_total):
        messages.error(request, "Insufficient wallet balance! Please add money to continue.")
        return redirect("add_money")

    try:
        with transaction.atomic():
            # Deduct wallet balance
            print("Wallet balance before deduction:", wallet.balance)
            wallet.balance = F('balance') - Decimal(final_total)
            wallet.save(update_fields=['balance'])
            
            print("Wallet balance after deduction:", wallet.balance," Deducted amount:", final_total)

            # Record wallet transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="debit",
                amount=Decimal(final_total),
                description=f"Payment for Order #{order.order_id}"
            )

            # Mark order as confirmed and paid
            order.payment_method = "wallet"
            order.status = "confirmed"
            order.save()
            print("Order confirmed:", order.order_id)

            # Move cart items to OrderItems & reduce stock
            cart_items = CartItems.objects.filter(user=user).select_related('variant')
            for ci in cart_items:
                if not OrderItem.objects.filter(order=order, product_variant=ci.variant).exists():
                    OrderItem.objects.create(
                    order=order,
                    product_variant=ci.variant,
                    quantity=ci.quantity,
                    price=ci.variant.price,
                )

                # Reduce product stock
                product = ci.variant.product
                product.stock = F('stock') - ci.quantity
                product.save(update_fields=['stock'])

            # Clear cart
            cart_items.delete()

            # If coupon applied -> mark used
            coupon_id = request.session.get("coupon_id")
            if coupon_id:
                try:
                    coupon = Coupon.objects.get(id=coupon_id)
                    order.coupon = coupon
                    order.save(update_fields=['coupon'])

                    user_coupon, _ = UserCoupon.objects.get_or_create(user=user, coupon=coupon)
                    user_coupon.used_count = F('used_count') + 1
                    user_coupon.save()
                except Coupon.DoesNotExist:
                    pass

            # Clear session coupon data
            request.session.pop("coupon_id", None)
            request.session.pop("discount", None)
            request.session.pop("final_total", None)

            # Create payment record
            Payment.objects.create(
                order=order,
                payment_method="wallet",
                payment_status="paid",
                paid_amount=Decimal(final_total),
                payment_gateway="Wallet"
            )
            print("Wallet payment successful for order:", order.order_id)

        return JsonResponse({
            "status": "success",
            "redirect_url": reverse("order_success", args=[order.order_id])
            })

    except Exception as e:
        print("Wallet payment error:", str(e))
        messages.error(request, "Payment failed. Please try again later.")
        return redirect("cart:cart")

#===================== RAZORPAY INTEGRATION ===============================

@csrf_exempt
@login_required(login_url="login")
def create_razorpay_order(request, order_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Get coupon-adjusted total from session
    final_total = request.session.get("final_total")
    if final_total is None:
        cart_items = CartItems.objects.filter(user=request.user).select_related('variant')
        final_total = sum(Decimal(item.variant.price) * item.quantity for item in cart_items)

    final_total = Decimal(str(final_total)).quantize(Decimal('0.01'))

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    razorpay_order = client.order.create({
        "amount": int(final_total * 100),
        "currency": "INR",
        "receipt": str(order.id),
        "payment_capture": 1
    })

    print("Razorpay order created:", razorpay_order)
    

    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "payment_method": "razorpay",
            "payment_status": "pending",
            "paid_amount": final_total,
            "payment_gateway": "Razorpay",
            "gateway_order_id": razorpay_order["id"]
        }
    )

    if created:
        payment.save()
        print("Payment created successfully.")

    if not created:
        payment.paid_amount = final_total
        payment.gateway_order_id = razorpay_order["id"]
        payment.payment_status = "pending"
        payment.save()
        print("Payment updated successfully.")

    return JsonResponse({
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": float(final_total),
        "currency": "INR",
    })

    # Verify Razorpay payment
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

        payment = get_object_or_404(Payment, gateway_order_id=razorpay_order_id)

        with transaction.atomic():
            # Update payment record
            payment.payment_status = "success"
            payment.gateway_payment_id = payment_id
            payment.gateway_signature = signature
            payment.paid_at = timezone.now()
            payment.save()

            # Update related Order
            order = payment.order
            order.status = "confirmed"
            order.payment_method = "razorpay"

            # Use session values (fallback to existing order values)
            session_final = request.session.get("final_total")
            session_discount = request.session.get("discount")
            if session_final:
                order.final_amount = Decimal(str(session_final)).quantize(Decimal('0.01'))
            if session_discount:
                order.discount_amount = Decimal(str(session_discount)).quantize(Decimal('0.01'))

            order.save()

            # Move cart items → OrderItems and decrease stock
            cart_items = CartItems.objects.filter(user=request.user).select_related('variant')
            for ci in cart_items:
                if not OrderItem.objects.filter(order=order, product_variant=ci.variant).exists():
                    OrderItem.objects.create(
                        order=order,
                        product_variant=ci.variant,
                        quantity=ci.quantity,
                        price=ci.variant.price,

                    )
                # decrease stock safely
                product = ci.variant.product
                product.stock = F('stock') - ci.quantity
                product.save(update_fields=['stock'])

            # Clear cart
            cart_items.delete()

            # If coupon applied in session -> attach to order and mark used
            coupon_id = request.session.get("coupon_id")
            if coupon_id:
                try:
                    coupon = Coupon.objects.get(id=coupon_id)
                    order.coupon = coupon
                    order.save(update_fields=['coupon'])

                    user_coupon, _ = UserCoupon.objects.get_or_create(user=request.user, coupon=coupon)
                    user_coupon.used_count = F('used_count') + 1
                    user_coupon.save()
                except Coupon.DoesNotExist:
                    pass

            # Clear coupon-related session keys
            request.session.pop("coupon_id", None)
            request.session.pop("discount", None)
            request.session.pop("final_total", None)

        print("Order placed successfully.", order.order_id)
        return JsonResponse({"status": "success", "order_id": str(order.order_id)})
    

    except razorpay.errors.SignatureVerificationError as e:
        print("Payment verification failed:", str(e))
        return JsonResponse({"status": "failed", "message": "Payment verification failed"}, status=400)
    except Exception as e:
        print("Verification error:", str(e))
        return JsonResponse({"status": "failed", "message": str(e)}, status=400)


#====================SAVE PAYMENT FAILURE  ============================

@login_required(login_url="login")
def save_payment_failure(request, order_id):
    print("Saving payment failure...", order_id)
    order = get_object_or_404(Order, id=order_id, user=request.user)
    request.session['failed_order_number'] = str(order.order_id)
    request.session['payment_failure_reason'] = "Payment failed or cancelled."
    return JsonResponse({'status': 'failure_saved'})

#====================PAYMENT FAILURE VIEW ============================
@login_required(login_url="login")
def payment_failure(request):
    print("Payment failed...")
    order_number = request.session.get('failed_order_number')
    failure_reason = request.session.get('payment_failure_reason', 'Payment failed. Please try again.')

    # ✅ Safe session cleanup (avoid KeyError)
    request.session.pop('failed_order_number', None)
    request.session.pop('payment_failure_reason', None)

    context = {
        'failure_reason': failure_reason,
        'order_number': order_number
    }
    return render(request, 'user/payment_failure.html', context)

#==================== PLACE ORDER VIEW ===============================
@login_required(login_url="login")
def place_order(request):
    cart_items = CartItems.objects.filter(user=request.user).select_related('variant')
    if not cart_items.exists():
        messages.error(request, "Your cart is empty!")
        return redirect("cart:cart")

    address_id = request.session.get("selected_address_id")
    if not address_id:
        messages.error(request, "Please select an address.")
        return redirect("select_address")
    address = Address.objects.get(id=address_id, user=request.user)

    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("select_payment")

    payment_method = request.POST.get("payment_method")
    if not payment_method:
        messages.error(request, "Please select a payment method.")
        return redirect("select_payment")

    # Calculate subtotal and session final_total
    subtotal = sum(Decimal(ci.variant.price) * ci.quantity for ci in cart_items)
    session_final = request.session.get("final_total")
    session_discount = request.session.get("discount")

    if session_final:
        final_amount = Decimal(str(session_final)).quantize(Decimal('0.01'))
    else:
        final_amount = Decimal(subtotal).quantize(Decimal('0.01'))

    discount_amount = Decimal(str(session_discount)) if session_discount else (Decimal(subtotal) - final_amount)

    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method=payment_method,
                total_amount=Decimal(subtotal).quantize(Decimal('0.01')),
                discount_amount=discount_amount.quantize(Decimal('0.01')),
                final_amount=final_amount,
                status="pending",
            )

            for ci in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_variant=ci.variant,
                    quantity=ci.quantity,
                    price=ci.variant.price,
                )
                # reduce stock
                product = ci.variant.product 
                product.stock = F('stock') - ci.quantity
                product.save(update_fields=['stock'])

            # Clear cart
            cart_items.delete()

            # If coupon applied -> attach and mark used (for COD we mark now)
            coupon_id = request.session.get("coupon_id")
            if coupon_id:
                try:
                    coupon = Coupon.objects.get(id=coupon_id)
                    order.coupon = coupon
                    order.save(update_fields=['coupon'])

                    user_coupon, _ = UserCoupon.objects.get_or_create(user=request.user, coupon=coupon)
                    user_coupon.used_count = F('used_count') + 1
                    user_coupon.save()
                except Coupon.DoesNotExist:
                    pass

            # Clear coupon session keys
            request.session.pop("coupon_id", None)
            request.session.pop("discount", None)
            request.session.pop("final_total", None)

            # Create Payment record for COD
            if payment_method == 'cod':
                Payment.objects.create(
                    order=order,
                    payment_method='cod',
                    payment_status='pending',
                    paid_amount=Decimal('0.00'),
                    payment_gateway='COD'
                )

        return redirect("order_success", order_id=order.order_id)

    except Exception as e:
        print("Order creation error:", str(e))
        messages.error(request, "Failed to place order. Please try again later.")
        return redirect("cart:cart")

@login_required(login_url="login")
def order_success(request, order_id):
    print(f"Order success for order_id: {order_id}")
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'user/order_success.html', {'order': order})

