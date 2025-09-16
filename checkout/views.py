from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from address.models import Address
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from cart.models import CartItems
from order.models import Order, OrderItem
from django.db import transaction

# Create your views here.
 #select address view
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

# add address view checkout page
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
    
#edit address view checkout page
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

        if not address.full_name or not address.phone_number or not address.address or not address.city or not address.district or not address.state or not address.country or not address.pincode:
            messages.error(request, "Please fill all the fields.")
            return redirect("edit_address", address_id=address_id)

        print("Address updated successfully.", address.full_name, address.street) 
        address.save() 
        messages.success(request, "Address updated successfully ")
        return redirect("select_address")
    
    return redirect("select_address")  # Always redirect to checkout

#selecr payment method view
@login_required(login_url="login")
def select_payment(request):
    if request.method == "POST":
        payment_method = request.POST.get("payment_method")

        if not payment_method:
            messages.error(request, "Please select a payment method.")
            return redirect("select_payment")

        # Save selected payment method to session
        request.session["payment_method"] = payment_method

        if payment_method == "cod":
            print("Cash on Delivery selected.")
            messages.success(request, "Cash on Delivery selected.")
        elif payment_method == "razorpay":
            print("Razorpay selected.")
            messages.success(request, "Razorpay selected.")
        # Redirect to confirmation 
        return redirect("checkout_summary")  # 
        

    return render(request, "user/select_payment.html")

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

        return redirect("checkout_summary")  # Thank you page

    except Exception as e:
        messages.error(request, f"Order failed: {e}")
        print("Order placement error:", e)
        return redirect("select_payment")
    

login_required(login_url="login")
def checkout_summary(request):
    return render(request, "user/order_success.html")
