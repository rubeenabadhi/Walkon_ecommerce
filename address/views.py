from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import *
from .forms import *

# Create your views here.

                                                                        #### Address Views ####
@login_required(login_url="login")
def address(request):
    addresses = Address.objects.filter(user=request.user).order_by("-id")
    paginator = Paginator(addresses, 2)  # 2 addresses per page

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "user/address.html", {
        "page_obj": page_obj,
        "addresses": page_obj,  # reuse in template loop
    })
                                                                 ###### add address #######
@login_required(login_url="login")
def add_address(request):    
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user # Set the user field to the logged-in user
            address.save()
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
            return redirect("address")
    else:
        form = AddressForm(instance=address)
    return render(request, "user/address_form.html", {"form": form})    

                                                                                    ##delete address###
@login_required(login_url="login")
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    address.delete()
    return redirect("address")  

