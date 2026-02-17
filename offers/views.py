from django.shortcuts import render
from  .models import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import F, Sum
from cart.models import CartItems
from .forms import CouponForm, ProductOfferForm, CategoryOfferForm
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_date


# Create your views here.

#==================================================================ADMIN COUPON MANAGEMENT========================================================
#=================================================================================================================================================
#----------- to display all coupons in admin panel-------------

@login_required(login_url='admin_login')
def admin_coupons(request):
    # Auto update coupon active status based on current date
    today = timezone.now().date()
    Coupon.objects.filter(valid_to__lt=today, active=True).update(active=False) #bulk update
    Coupon.objects.filter(valid_to__gte=today, active=False).update(active=True)
    coupons = Coupon.objects.all().order_by('-created_at')

    # Search by code
    search_query = request.GET.get('search')
    if search_query:
        coupons = coupons.filter(code__icontains=search_query)

    # Filter by status (active/inactive)
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        coupons = coupons.filter(active=True)
    elif status_filter == 'inactive':
        coupons = coupons.filter(active=False)

    # Filter by discount type
    discount_type = request.GET.get('discount_type')
    if discount_type in ['percentage', 'fixed']:
        coupons = coupons.filter(discount_type=discount_type)

    # Filter by date range (valid_from)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        coupons = coupons.filter(valid_from__date__gte=parse_date(start_date))
    if end_date:
        coupons = coupons.filter(valid_to__date__lte=parse_date(end_date))

    # Pagination
    paginator = Paginator(coupons, 10)  # 10 per page
    page_number = request.GET.get('page', 10)
    page_obj = paginator.get_page(page_number)

    context = {
        'coupons': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'discount_type': discount_type,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'admin/coupons.html', context)

#=================users used coupons===================

@login_required(login_url='admin_login')
def users_used_coupons(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    user_coupons = UserCoupon.objects.filter(coupon=coupon).select_related('user')
    paginator = Paginator(user_coupons, 10)  # 10 per page
    page_number = request.GET.get('page', 10) #1 means 
    page_obj = paginator.get_page(page_number)

    context = {
        'coupon': coupon,
        'user_coupons': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'admin/coupon_users.html', context)

# ==========to load coupon form for add and edit=============
@login_required(login_url='admin_login')
def load_coupon_form(request, pk=None):
    if pk:
        coupon = get_object_or_404(Coupon, pk=pk)
        form = CouponForm(instance=coupon)
    else:
        form = CouponForm()
    html = render_to_string('admin/coupon_form_partial.html', {'form': form}, request=request)
    return JsonResponse({'html': html})


# ==========to save coupon form for add and edit=============
@login_required(login_url='admin_login')
def save_coupon(request, pk=None):
    if pk:
        coupon = get_object_or_404(Coupon, pk=pk)
        form = CouponForm(request.POST, instance=coupon)
        print("Editing Coupon")
    else:
        print("Adding Coupon")
        form = CouponForm(request.POST)

    if form.is_valid():
        coupon = form.save()
        data = {
            'success': True,
            'coupon': {
                'id': coupon.id,
                'code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': str(coupon.discount_value),
                'valid_from': coupon.valid_from.strftime('%d-%m-%y %H:%M'),
                'valid_to': coupon.valid_to.strftime('%d-%m-%y %H:%M'),
            }
        }
        print(data)
        return JsonResponse(data)
    else:
        print(form.errors)
        html = render_to_string('admin/coupon_form_partial.html', {'form': form}, request=request)
        return JsonResponse({'success': False, 'html': html})
    
# ==========to delete coupon=============
@login_required(login_url='admin_login')
def delete_coupon(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    messages.success(request, "Coupon deleted successfully.")
    return redirect('admin_coupons')


#========Refer & Earn========
@login_required(login_url='admin_login')
def admin_referrals(request):
    referrals = Referral.objects.all().order_by('-created_at')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        referrals = referrals.filter(referrer__username__icontains=search_query)

    # Status filter (optional: active/inactive)
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        referrals = referrals.filter(referrer__is_active=True)
    elif status_filter == 'inactive':
        referrals = referrals.filter(referrer__is_active=False)

    # Pagination
    paginator = Paginator(referrals, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'referrals': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'admin/referral_users.html', context)

#=======================PRODUCT OFFER MANAGEMENT==========================
@login_required(login_url='admin_login')
def admin_product_offers(request):
    offers = ProductOffer.objects.all().order_by('-created_at')

    # Search by product name
    search_query = request.GET.get('search')
    if search_query:
        offers = offers.filter(product__name__icontains=search_query)

    # Status filter (optional: active/inactive)
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        offers = offers.filter(is_active=True)
    elif status_filter == 'inactive':
        offers = offers.filter(is_active=False)

    # Pagination
    paginator = Paginator(offers, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'offers': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'admin/product_offers.html', context)

#==========to load product offer form for add and edit=============
@login_required(login_url='admin_login')
def load_product_offer_form(request, pk=None):
    if pk:
        offer = get_object_or_404(ProductOffer, pk=pk)
        form = ProductOfferForm(instance=offer)
    else:
        form = ProductOfferForm()
    html = render_to_string('admin/product_offer_form_partial.html', {'form': form}, request=request)
    return JsonResponse({'html': html})
#==========to save product offer form for add and edit=============
@login_required(login_url='admin_login')
def save_product_offer(request, pk=None):
    if pk:
        offer = get_object_or_404(ProductOffer, pk=pk)
        form = ProductOfferForm(request.POST, instance=offer)
        print("Editing Product Offer")
    else:
        print("Adding Product Offer")
        form = ProductOfferForm(request.POST)

    if form.is_valid():
        offer = form.save()
        data = {
            'success': True,
            'offer': {
                'id': offer.id,
                'product': offer.product.name,
                'discount_percentage': offer.discount_percentage,
                'valid_from': offer.valid_from.strftime('%d-%m-%y %H:%M'),
                'valid_to': offer.valid_to.strftime('%d-%m-%y %H:%M'),
            }
        }
        print(data)
        return JsonResponse(data)
    else:
        print(form.errors)
        html = render_to_string('admin/product_offer_form_partial.html', {'form': form}, request=request)
        return JsonResponse({'success': False, 'html': html})

   
#===============delete product offer=============

@login_required(login_url='admin_login')
def delete_product_offer(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)
    offer.delete()
    messages.success(request, "Product offer deleted successfully.")
    return redirect('admin_product_offers')

#===============Category Offer Management=======================

@login_required(login_url='admin_login')
def admin_category_offers(request):
    offers = CategoryOffer.objects.all().order_by('-created_at')    

    # Search by category name
    search_query = request.GET.get('search')
    if search_query:
        offers = offers.filter(category__name__icontains=search_query)

    # Status filter (optional: active/inactive)
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        offers = offers.filter(is_active=True)
    elif status_filter == 'inactive':
        offers = offers.filter(is_active=False)

    # Pagination
    paginator = Paginator(offers, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'offers': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
    }

    return render(request, 'admin/category_offers.html', context)

#==========to load category offer form for add and edit=============
@login_required(login_url='admin_login')    
def load_category_offer_form(request, pk=None):
    if pk:
        offer = get_object_or_404(CategoryOffer, pk=pk)
        form = CategoryOfferForm(instance=offer)
    else:
        form = CategoryOfferForm()
    html = render_to_string('admin/category_offer_form_partial.html', {'form': form}, request=request)
    return JsonResponse({'html': html})
#==========to save category offer form for add and edit=============
@login_required(login_url='admin_login')
def save_category_offer(request, pk=None):
    if pk:
        offer = get_object_or_404(CategoryOffer, pk=pk)
        form = CategoryOfferForm(request.POST, instance=offer)
        print("Editing Category Offer")

    else:
        print("Adding Category Offer")
        form = CategoryOfferForm(request.POST)

    if form.is_valid():
        offer = form.save()
        data = {
            'success': True,
            'offer': {
                'id': offer.id,
                'category': offer.category.name,
                'discount_percentage': offer.discount_percentage,
                'valid_from': offer.valid_from.strftime('%d-%m-%y %H:%M'),
                'valid_to': offer.valid_to.strftime('%d-%m-%y %H:%M'),
            }
        }
        print(data)
        return JsonResponse(data)
    else:
        print(form.errors)
        html = render_to_string('admin/category_offer_form_partial.html', {'form': form}, request=request)
        return JsonResponse({'success': False, 'html': html})
    
#===============delete category offer=============
@login_required(login_url='admin_login')
def delete_category_offer(request, pk): 
    offer = get_object_or_404(CategoryOffer, pk=pk)
    offer.delete()
    messages.success(request, "Category offer deleted successfully.")
    return redirect('admin_category_offers')

#=====get best offer====


def get_best_offer(product):
    now = timezone.now()

    product_offer = ProductOffer.objects.filter(
        product=product, is_active=True, valid_from__lte=now, valid_to__gte=now
    ).first()

    category_offer = CategoryOffer.objects.filter(
        category=product.category, is_active=True, valid_from__lte=now, valid_to__gte=now
    ).first()

    product_discount = product_offer.discount_percentage if product_offer else 0
    category_discount = category_offer.discount_percentage if category_offer else 0

    return max(product_discount, category_discount)

#===========================================================================USER VIEW TO APPLY COUPON==============================================
#==================================================================================================================================================

#=-----------view couons in user------
def available_coupons(request):
    if not request.user.is_authenticated:
        return redirect("login")

    now = timezone.localtime(timezone.now())  #  converts UTC → local timezone

    coupons = Coupon.objects.filter(active=True, valid_from__lte=now, valid_to__gte=now)

    # Debugging logs
    print("Current time:", now)
    filtered = coupons.filter(active=True, valid_from__lte=now, valid_to__gte=now)
    print("Filtered coupons:", list(filtered.values('code', 'valid_from', 'valid_to')))

    # Filter out coupons already fully used by the user
    available = []
    for coupon in coupons:
        user_coupon = UserCoupon.objects.filter(user=request.user, coupon=coupon).first() #get usage record
        if not user_coupon or user_coupon.used_count < coupon.usage_limit: # means can still use it 
            available.append(coupon)

    return render(request, 'user/user_coupons.html', {'coupons': available})

#=-----------to apply coupon in user------
@login_required(login_url='login')
@require_POST
def apply_coupon(request):
    print("Applying coupon...")
    code = request.POST.get("coupon_code", "").strip()
    if not code:
        return JsonResponse({"status": "error", "message": "Please enter a coupon code."})

    try:
        coupon = Coupon.objects.get(code__iexact=code, active=True)
    except Coupon.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Invalid coupon code"})

    now = timezone.now()
    if not (coupon.valid_from <= now <= coupon.valid_to):
        return JsonResponse({"status": "error", "message": "This coupon is not valid now"})

    # Check user usage limit via UserCoupon (do NOT increase used_count here)
    user_coupon, _ = UserCoupon.objects.get_or_create(user=request.user, coupon=coupon)
    if user_coupon.used_count >= coupon.usage_limit:
        return JsonResponse({"status": "error", "message": "You have already used this coupon maximum times"})

    # Calculate cart total
    cart_items = CartItems.objects.filter(user=request.user).select_related("variant")
    total_price = sum(Decimal(item.variant.get_offer_price()) * item.quantity for item in cart_items)
    print("Cart total price:", total_price)

    if total_price < coupon.min_order_amount:
        return JsonResponse({
            "status": "error",
            "message": f"Minimum order amount for this coupon is ₹{coupon.min_order_amount}"
        })

    # Calculate discount depending on type
    if coupon.discount_type == 'percentage':
        discount = (total_price * (Decimal(coupon.discount_value) / Decimal('100'))).quantize(Decimal('0.01'))
    else:
        discount = Decimal(coupon.discount_value).quantize(Decimal('0.01'))

    # Ensure discount doesn't exceed subtotal
    discount = min(discount, total_price)
    final_total = (total_price - discount).quantize(Decimal('0.01'))

    # Save coupon to session (do NOT mark used yet)
    request.session["coupon_id"] = str(coupon.id)
    request.session["discount"] = str(discount)           # string for safe session storage
    request.session["final_total"] = str(final_total)

    return JsonResponse({
        "status": "success",
        "message": f'Coupon "{coupon.code}" applied successfully!',
        "applied_coupon": {"code": coupon.code},
        "discount": str(discount),
        "final_total": str(final_total)
    })

#=-----------to remove coupon in user------
@login_required(login_url='login')
@require_POST
def remove_coupon(request):
    request.session.pop("coupon_id", None)
    request.session.pop("discount", None)
    request.session.pop("final_total", None)

    cart_items = CartItems.objects.filter(user=request.user).select_related("variant")
    total_price = sum(Decimal(item.variant.get_offer_price()) * item.quantity for item in cart_items)
    total_price = Decimal(total_price).quantize(Decimal('0.01'))

    # Update session final_total to fallback to subtotal
    request.session["final_total"] = str(total_price)

    return JsonResponse({
        "status": "success",
        "message": "Coupon removed",
        "final_total": str(total_price),
        "applied_coupon": None,
        "discount": "0"
    })

#=======================REFER & EARN==========================


@login_required(login_url='/signup/')
def refer_earn(request):
    user = request.user
    referral_code = None

    try:
        referral = Referral.objects.get(referrer=user)
        referral_code = referral.referral_code
    except Referral.DoesNotExist:
        referral_code = "No referral code found"

    context = {
        'referral_code': referral_code
    }
    return render(request, 'user/refer_earn.html', context)

#=======================MY REFERRALS==========================


def my_referrals(request):
    user = request.user
    referred_users = [] # Initialize referred_users to an empty list in case the referral record doesn't exist

    try:
        referral = Referral.objects.get(referrer=user) #get referral record for current user
        referred_users = referral.referred_users.all() # get all users referred by current user through the referral record
    except Referral.DoesNotExist:
        # User has no referral record yet
        referred_users = []
    paginator=Paginator(referred_users,10)
    page_number=request.GET.get('page')
    page_obj=paginator.get_page(page_number)

    context = {
        'referred_users': page_obj,
         'page_obj': page_obj,
    }
    return render(request, 'user/my_referrals.html', context)



