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
from .utils import calculate_final_amount
from django.core.exceptions import ValidationError
import logging

admin_logger = logging.getLogger('admin_logger')
user_logger = logging.getLogger('user_logger')

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))



# Create your views here.
 #===========================================select address view =================================
@login_required(login_url="login")
def select_address(request):
    addresses = Address.objects.filter(user=request.user)
    if request.method == "POST":
        selected_address_id = request.POST.get("selected_address") # Get the selected address ID
        
        if selected_address_id:
            selected_address = get_object_or_404(Address, id=selected_address_id, user=request.user)

            request.session['selected_address_id'] = selected_address.id
            user_logger.info("Selected Address ", selected_address.full_name,selected_address.city)  # Debugging line
            messages.success(request, "Address selected successfully.")
            return redirect("select_payment")  # Redirect to payment page after selecting address
        else:
            user_logger.info(f"No address selected for user {request.user.username}.")
            messages.error(request, "Please select an address.")
            return redirect("select_address")
    return render(request, "user/select_address.html", {"addresses": addresses})

# =======================================add address view checkout page=========================
@login_required(login_url="login")
def add_address_checkout(request):
    if request.method == "POST":
        address=Address(
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
    try:
        address.full_clean()  # Validate the model fields
        address.save()
        user_logger.info("Address added successfully for user:", request.user)
        return JsonResponse({"status": "success", "message": "Address saved successfully!"})
    
    except ValidationError as e:
        user_logger("Validation error:", e) #e means the error message from validation
        return JsonResponse({"status": "error", "errors": e.message_dict}, status=400)
    
#=======================================edit address view checkout page ==========================


@login_required(login_url="login")
def edit_address_checkout(request, address_id):
    user_logger.info("Editing Address ID:", address_id, request.user) # 
    if request.method == "POST":
        address = get_object_or_404(Address, id=address_id, user=request.user)
        user_logger.info("Editing Address ID:", address.user)  
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
            return JsonResponse({"status": "error", "message": "All fields are required."}, status=400)
    
        try:
            address.full_clean()  # Validate the model fields
            address.save()
            user_logger.info("Address updated successfully for user:", request.user)
            return JsonResponse({"status": "success", "message": "Address updated successfully!"})
        except ValidationError as e:
            user_logger.error("Validation error:", e)
            return JsonResponse({"status": "error", "errors": e.message_dict}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)

#------------get delivery charge function------
def get_delivery_charge(state):
    if state and 'kerala' in state.lower():
        return Decimal('50.00')  # Within Kerala
    return Decimal('150.00')  # Outside Kerala or state not provided

#======================================selecr payment method view =========================
@login_required(login_url="login")
def select_payment(request):
    user_logger.info(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)  # Debugging line
    cart_items = CartItems.objects.filter(user=request.user).select_related('variant')
    if not cart_items.exists():
        messages.error(request, "Your cart is empty!")
        return redirect("cart:cart")

    address_id = request.session.get("selected_address_id")
    if not address_id:
        messages.error(request, "Please select an address.")
        return redirect("select_address")

    address = Address.objects.get(id=address_id, user=request.user)

    # subtotal calculation 
    subtotal = sum(Decimal(item.variant.get_offer_price()) * item.quantity for item in cart_items)

    # take coupon from session if any
    coupon = None
    coupon_id = request.session.get("coupon_id")
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id, active=True).first()
        user_logger.info(f"Applying coupon in select payment:{coupon} for user {request.user.username}.")

    # calculate final amount along with discount from utils.py
    _, discount, final_total = calculate_final_amount(cart_items, coupon)
    user_logger.info("Select Payment - Subtotal:", subtotal, "Discount:", discount, "Final Total:", final_total)
    # delivery charge calculation
    delivery_charge = get_delivery_charge(address.state)
    final_total += delivery_charge
    user_logger.info("Delivery Charge:", delivery_charge, "New Final Total:", final_total)
    #sessio storage for final amount and discount to be used in payment processing views
    request.session["final_total"] = float(final_total)  # Convert Decimal to float for JSON serialization

    # pending order update or create 
    order = Order.objects.filter(user=request.user, payment_method="pending").last()  

    if not order:
        order = Order.objects.create(
            user=request.user,
            address=address,
            delivery_charge=delivery_charge,
            total_amount=subtotal,
            discount_amount=discount,
            final_amount=final_total,
            payment_method="pending",
            status="pending",
            coupon=coupon
        )
    else:
        # update existing pending order with latest amounts 
        order.delivery_charge = delivery_charge
        order.total_amount = subtotal
        order.discount_amount = discount
        order.final_amount = final_total
        order.coupon = coupon
        order.save(update_fields=['total_amount', 'discount_amount', 'final_amount', 'coupon', 'delivery_charge'])

    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    now = timezone.localtime(timezone.now())
    coupons = Coupon.objects.filter(active=True, valid_from__lte=now, valid_to__gte=now)
    available = []
    for coupon in coupons:
        user_coupon = UserCoupon.objects.filter(user=request.user, coupon=coupon).first() #get usage record
        if not user_coupon or user_coupon.used_count < coupon.usage_limit: # means can still use it 
            available.append(coupon)

    context = {
        "cart_items": cart_items,
        "address": address,
        "order": order,
        "total_price": subtotal.quantize(Decimal('0.01')),     # Subtotal
        "delivery_charge": delivery_charge.quantize(Decimal('0.01')),
        "final_total": final_total.quantize(Decimal('0.01')),   # Grand Total (discounted)
        "discount": discount.quantize(Decimal('0.01')),
        "wallet_balance": wallet.balance,
        "available_coupons": available
    }

    return render(request, "user/select_payment.html", context)

# ==================== WALLET PAYMENT VIEW ===============================
@csrf_exempt
@login_required(login_url="login")
def wallet_payment(request, order_id):
    user_logger.info("Incoming ORDER ID:", order_id)
    if request.method != "POST":
        user.logger.error("Invalid method:", request.method)
        return JsonResponse({"error": "Invalid request method"}, status=400)

    user = request.user
    wallet = get_object_or_404(Wallet, user=user)
    user_logger.info("Wallet balance BEFORE payment:", wallet.balance)

    order = Order.objects.create(user=user, status="pending", payment_method="wallet")  # Temporary order object for validation,
    if order.status != "pending":
        user_logger.error("Order already processed")
        return JsonResponse({
            "status": "failed",
            "message": "Order already processed."
        }, status=400)

    # FETCH CART ITEMS
    cart_items = CartItems.objects.filter(user=user).select_related("variant", "product")
    user_logger.info("Cart item count =", cart_items.count())

    if not cart_items.exists():
        return JsonResponse({"status": "failed", "message": "Cart is empty"}, status=400)

    # SUBTOTAL + DISCOUNT + FINAL TOTAL
    subtotal = sum(Decimal(ci.variant.get_offer_price()) * ci.quantity for ci in cart_items)

    session_final = request.session.get("final_total")
    session_discount = request.session.get("discount")
    user_logger.info(" session_final:", session_final, "session_discount:", session_discount, "subtotal:", subtotal)

    if session_final:
        final_total = Decimal(str(session_final)).quantize(Decimal('0.01'))
    else:
        _, discount_calc, final_total = calculate_final_amount(cart_items, None)
        final_total = final_total.quantize(Decimal('0.01'))
        session_discount = session_discount or discount_calc

    user_logger.info(" final_total:", final_total)
    discount_amount = Decimal(str(session_discount)) if session_discount else (Decimal(subtotal) - final_total)
    user_logger.info("discount_amount:", discount_amount)
    # coupon
    coupon = None
    coupon_id = request.session.get("coupon_id")

    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()
        user_logger.info(" coupon object:", coupon)

    # WALLET BALANCE CHECK
    user_logger.info(" Wallet balance CHECK:", wallet.balance, "<", final_total)
    if wallet.balance < final_total:
        user_logger.error(" Insufficient wallet balance")
        return JsonResponse({
            "status": "failed",
            "message": "Insufficient wallet balance"
        }, status=400)
    
    # MAIN TRANSACTION BLOCK
    # -------------------------------
    try:
        with transaction.atomic():

            for ci in cart_items:
                user_logger.info(f" Checking item → VariantID:{ci.variant.id}, Qty:{ci.quantity}")

                if not OrderItem.objects.filter(order=order, product_variant=ci.variant).exists():
                    OrderItem.objects.create(
                        order=order,
                        product_variant=ci.variant,
                        quantity=ci.quantity,
                        price=ci.variant.get_offer_price(),
                    )
                    # STOCK REDUCE
                    variant = ci.variant
                    user_logger.info(" Before Stock:", variant.stock)
                    variant.stock = F("stock") - ci.quantity
                    variant.save(update_fields=["stock"])
                    variant.refresh_from_db()
                    user_logger.info(" After Stock:", variant.stock)
                else:
                    # if item already exists
                    user_logger.info(" OrderItem already exists → Skipped")

            # clear cart
            cart_items.delete()
            # Duplicate transaction check
            if WalletTransaction.objects.filter(
                wallet=wallet,
                transaction_type="debit",
                amount=final_total,
                description__icontains=f"Wallet Payment for Order #{order.order_id}"
            ).exists():
                user_logger.error("DEBUG: Duplicate wallet transaction detected")
                raise Exception("Duplicate wallet transaction detected")
            # -------------------------------

            # WALLET DEDUCT
            wallet.balance = F("balance") - final_total
            wallet.save(update_fields=["balance"])
            wallet.refresh_from_db()
            user_logger.info("DEBUG: Wallet balance AFTER deduction:", wallet.balance)

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="debit",
                amount=final_total,
                order=order,
                purpose="order_payment",

                description=f"Wallet Payment for Order #{order.order_id}",
            )

            # UPDATE ORDER
            order.payment_method = "wallet"
            order.status = "confirmed"
            order.total_amount = subtotal
            order.discount_amount = discount_amount
            order.final_amount = final_total
            order.coupon = coupon
            # copy address snapshot from session
            address_id = request.session.get("selected_address_id")
            if address_id:
                address = get_object_or_404(Address, id=address_id, user=user)
                order.full_name = address.full_name
                order.phone_number = address.phone_number
                order.full_address = address.address
                order.street = address.street
                order.city = address.city
                order.state = address.state
                order.district = address.district
                order.country = address.country
                order.pincode = address.pincode 
            delivery_charge = get_delivery_charge(order.state)
            order.delivery_charge = delivery_charge
            order.save()
            user_logger.info("Order updated","delevery_charge", delivery_charge)

            # -------------------------------
            # COUPON USAGE
            # -------------------------------
            if coupon:
                user_logger.info("DEBUG: Updating coupon usage")
                user_coupon, _ = UserCoupon.objects.get_or_create(user=user, coupon=coupon)
                user_coupon.used_count = F("used_count") + 1
                user_coupon.save()

            # -------------------------------
            # PAYMENT RECORD
            # -------------------------------
            user_logger.info("DEBUG: Creating Payment record")
            payment, _ = Payment.objects.get_or_create(order=order)
            payment.payment_method = "wallet"
            payment.payment_status = "success"
            payment.paid_amount = final_total
            payment.payment_gateway = "Wallet"
            payment.paid_at = timezone.now()
            payment.save()

            # CLEAR COUPON SESSION
            request.session.pop("coupon_id", None)
            request.session.pop("discount", None)
            request.session.pop("final_total", None)

            user_logger.info("=== WALLET PAYMENT SUCCESS ===")
        return JsonResponse({
            "status": "success",
            "order_id": order.order_id,
            "redirect_url": reverse("order_success", args=[order.order_id])
        })

    except Exception as e:
        user_logger.error(" WALLET ERROR:", str(e))
        return JsonResponse({"status": "failed", "message": str(e)}, status=500)

#===================== RAZORPAY INTEGRATION ===============================
@login_required(login_url="login")
def create_razorpay_order(request, order_id):

    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)

    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Order must be pending
    if order.status != "pending":
        return JsonResponse({
            "status": "failed",
            "message": "Order already processed"
        }, status=404)

    # Final amount from session (preferred)
    final_total = order.final_amount

    if final_total is None:
        cart_items = CartItems.objects.filter(user=request.user).select_related("variant")
        final_total = sum(Decimal(ci.variant.get_offer_price()) * ci.quantity for ci in cart_items)

    final_total = Decimal(str(final_total)).quantize(Decimal('0.01'))  # safe

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    razorpay_order = client.order.create({
        "amount": int(final_total * 100),
        "currency": "INR",
        "receipt": str(order.id),
        "payment_capture": 1

    })

    # Create or update payment record
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "payment_method": "razorpay",
            "payment_status": "pending",
            "paid_amount": final_total,
            "payment_gateway": "Razorpay",
            "paid_at": timezone.now(),
            "gateway_order_id": razorpay_order["id"]
        }
    )
    user_logger.info("final_total:", final_total)

    if not created:
        payment.paid_amount = final_total
        payment.gateway_order_id = razorpay_order["id"]
        payment.payment_status = "pending",
        payment.save()

    return JsonResponse({
        "razorpay_order_id": razorpay_order["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": float(final_total),
        "currency": "INR",
    })


#==================== RAZORPAY PAYMENT VERIFICATION ===========================
@csrf_exempt
@login_required(login_url="login")
def verify_razorpay_payment(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)

    payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    signature = request.POST.get("razorpay_signature")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        # Verify signature
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })

        payment = get_object_or_404(Payment, gateway_order_id=razorpay_order_id)
        order = payment.order

        if order.status != "pending":
            return JsonResponse({
                "status": "failed",
                "message": "Order already processed"
            }, status=400)

        with transaction.atomic():

            # 1) Update payment
            payment.payment_status = "success"
            payment.gateway_payment_id = payment_id
            payment.gateway_signature = signature
            payment.paid_at = timezone.now()
            payment.save()

            # 2) Update order
            order.status = "confirmed"
            order.payment_method = "razorpay"

            # Use session values if available
            session_final = request.session.get("final_total")
            session_discount = request.session.get("discount")

            if session_final:
                order.final_amount = Decimal(str(session_final)).quantize(Decimal('0.01'))
                user_logger.info("Order final amount from session:", order.final_amount)
            if session_discount:
                order.discount_amount = Decimal(str(session_discount)).quantize(Decimal('0.01'))
                user_logger.info("Order discount amount from session:", order.discount_amount)
            # copy address snapshot from session
            address_id = request.session.get("selected_address_id")
            if address_id:
                address = get_object_or_404(Address, id=address_id, user=request.user)
                order.address = address
                order.full_name = address.full_name
                order.phone_number = address.phone_number
                order.street = address.street
                order.city = address.city
                order.state = address.state
                order.district = address.district
                order.pincode = address.pincode
                order.country = address.country
                order.full_address = address.address    

            
            order.save()

            # 3) Move Cart Items to Order Items
            cart_items = CartItems.objects.filter(user=request.user).select_related("variant")

            for ci in cart_items:
                if not OrderItem.objects.filter(order=order, product_variant=ci.variant).exists():
                    OrderItem.objects.create(
                        order=order,
                        product_variant=ci.variant,
                        quantity=ci.quantity,
                        price=ci.variant.get_offer_price(),
                    )

                # Reduce stock
                variant = ci.variant
                user_logger.info("DEBUG: Before Stock:", variant.stock)
                variant.stock = F("stock") - ci.quantity
                variant.save(update_fields=["stock"])

            # Clear cart
            cart_items.delete()

            # 4) Coupon update
            coupon_id = request.session.get("coupon_id")
            if coupon_id:
                coupon = Coupon.objects.filter(id=coupon_id).first()
                if coupon:
                    order.coupon = coupon
                    order.save()

                    user_coupon, _ = UserCoupon.objects.get_or_create(user=request.user, coupon=coupon)
                    user_coupon.used_count = F("used_count") + 1
                    user_coupon.save()

            # Clear session
            request.session.pop("coupon_id", None)
            request.session.pop("discount", None)
            request.session.pop("final_total", None)

        return JsonResponse({
            "status": "success",
            "order_id": str(order.order_id)
        })

    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"status": "failed", "message": "Payment verification failed"}, status=400)

    except Exception as e:
        user_logger.error("Verification error:", str(e))
        return JsonResponse({"status": "failed", "message": str(e)}, status=400)

#====================SAVE PAYMENT FAILURE  ============================

@login_required(login_url="login")
def save_payment_failure(request, order_id):
    user_logger.info("Saving payment failure...", order_id)
    order = get_object_or_404(Order, id=order_id, user=request.user)
    request.session['failed_order_number'] = str(order.order_id)
    request.session['payment_failure_reason'] = "Payment failed or cancelled."
    return JsonResponse({'status': 'failure_saved'})

#====================PAYMENT FAILURE VIEW ============================
@login_required(login_url="login")
def payment_failure(request):
    user_logger.info("Payment failed...")
    order_number = request.session.get('failed_order_number')
    failure_reason = request.session.get('payment_failure_reason', 'Payment failed. Please try again.')

    #  Safe session cleanup (avoid KeyError)
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

    # Ensure address
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

    # Price calculation
    subtotal = sum(Decimal(ci.variant.get_offer_price()) * ci.quantity for ci in cart_items)

    session_final = request.session.get("final_total")
    session_discount = request.session.get("discount")

    if session_final:
        final_amount = Decimal(str(session_final)).quantize(Decimal('0.01'))
    else:
        _, discount_calc, final_amount = calculate_final_amount(cart_items, None)
        final_amount = final_amount.quantize(Decimal('0.01'))
        session_discount = session_discount or discount_calc

    discount_amount = Decimal(str(session_discount)) if session_discount else (Decimal(subtotal) - final_amount)
    delivery_charge=get_delivery_charge(address.state)
    
    if payment_method == "cod" and final_amount >= 1000:
        messages.error(request, "Cash on Delivery is not available for orders above ₹1000.")
        user_logger.info('final amount',final_amount)
        return redirect("select_payment")

    try:
        with transaction.atomic():
            # Create order and order items 
            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method=payment_method,
                total_amount=Decimal(subtotal).quantize(Decimal('0.01')),
                discount_amount=Decimal(discount_amount).quantize(Decimal('0.01')),
                delivery_charge=delivery_charge,
                final_amount=final_amount,
                status="pending",

                full_name=address.full_name,
                phone_number=address.phone_number,
                full_address=address.address,
                street=address.street,
                city=address.city,
                state=address.state,
                district=address.district,
                country=address.country,
                pincode=address.pincode,
            )

            # Order items
            for ci in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_variant=ci.variant,
                    quantity=ci.quantity,
                    price=ci.variant.get_offer_price(),
                )

                variant = ci.variant
                user_logger.info("DEBUG: Before Stock:", variant.stock)    
                variant.stock = F('stock') - ci.quantity
                variant.save(update_fields=['stock'])

            # Clear cart
            cart_items.delete()

            # Handle coupon
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

            # Clear coupon session
            request.session.pop("coupon_id", None)
            request.session.pop("discount", None)
            request.session.pop("final_total", None)

            # COD payment entry
            if payment_method == "cod":
                Payment.objects.create(
                    order=order,
                    payment_method="cod",
                    payment_status="pending",
                    paid_amount=Decimal('0.00'),
                    payment_gateway="COD",
                    created_at=timezone.now()
                )
    


        return redirect("order_success", order_id=order.order_id)
    

    except Exception as e:
        user_logger.error("Order creation error:", str(e))
        messages.error(request, "Failed to place order. Please try again later.")
        return redirect("cart:cart")

#==================== ORDER SUCCESS VIEW ===============================
@login_required(login_url="login")
def order_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Prefer stored values (saved during place_order / payment)
    subtotal = order.total_amount or Decimal('0.00')
    discount_amount = order.discount_amount or Decimal('0.00')
    final_total = order.final_amount or (subtotal - discount_amount)

    # safe quantize for display
    subtotal = Decimal(subtotal).quantize(Decimal('0.01'))
    discount_amount = Decimal(discount_amount).quantize(Decimal('0.01'))
    final_total = Decimal(final_total).quantize(Decimal('0.01'))
    # update order with unchanged amount
    order.unchanged_amount = final_total
    order.unchanged_discount = discount_amount
    order.save(update_fields=['unchanged_amount','unchanged_discount'])

    user_logger.info(order.unchanged_amount, order.unchanged_discount)
    # clear any session keys used in checkout (optional)
    request.session.pop("coupon_id", None)
    request.session.pop("final_total", None)
    request.session.pop("discount", None)

    context = {
        'order': order,
        'discount_amount': discount_amount,
        'subtotal': subtotal,
        'final_total': final_total,
    }
    return render(request, 'user/order_success.html', context)
