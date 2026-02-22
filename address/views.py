from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import *
from .forms import *
from order.models import Order
import logging

admin_logger = logging.getLogger('admin_logger')
user_logger = logging.getLogger('user_logger')

# ===========================================================================USER VIEW===============================================
#============================== Address Views ####
@login_required(login_url="login")
def address(request):
    user_logger.info(f"User {request.user.username} accessed the address page.")
    addresses = Address.objects.filter(user=request.user).order_by("-id")
    paginator = Paginator(addresses, 4)  # 4 addresses per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "user/address.html", {
        "page_obj": page_obj,
        "addresses": page_obj, # for loop in template insted of page_obj 
    })
######======================================= add address #######
@login_required(login_url="login")
def add_address(request):    
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user # Set the user field to the logged-in user
            address.save()
            user_logger.info(f"User {request.user.username} added an address.")
            messages.success(request, "Address added successfully.")
            return redirect("address")
        else:
            messages.error(request, "Form is invalid.")
            return redirect("add_address")
    else:
        form = AddressForm()
    return render(request, "user/address_form.html", {"form": form})

                                                                                    ##edit address###
@login_required(login_url="login")  
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            user_logger.info(f"User {request.user.username} edited an address.")
            messages.success(request, "Address updated successfully.")
            return redirect("address")
    else:
        form = AddressForm(instance=address)
    return render(request, "user/address_form.html", {"form": form})    

                                                                                    ##delete address###
@login_required(login_url="login")
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    Order.objects.filter(address=address).update(address=None) # means address will be null in order model
    # Now delete the address safely
    address.delete()
    user_logger.info(f"User {request.user.username} deleted an address.")
    messages.success(request, "Address deleted successfully.")
    return redirect("address")

