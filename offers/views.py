from django.shortcuts import render
from  .models import *
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import F, Sum
from cart.models import CartItems
from .forms import CouponForm, ProductOfferForm, ProductOfferForm
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from decimal import Decimal
from django.views.decorators.http import require_POST

# Create your views here.

#==================================================================ADMIN COUPON MANAGEMENT========================================================
#=================================================================================================================================================
#----------- to display all coupons in admin panel-------------
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date

@login_required(login_url='admin_login')
def admin_coupons(request):
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



#===========================================================================USER VIEW TO APPLY COUPON==============================================
#==================================================================================================================================================

#=-----------view couons in user------
def available_coupons(request):
    if not request.user.is_authenticated:
        return redirect("login")

    now = timezone.now()
    coupons = Coupon.objects.filter(active=True, valid_from__lte=now, valid_to__gte=now)

    # Filter out coupons already fully used by the user
    available = []
    for coupon in coupons:
        user_coupon = UserCoupon.objects.filter(user=request.user, coupon=coupon).first()
        if not user_coupon or user_coupon.used_count < coupon.usage_limit:
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
    total_price = sum(Decimal(item.variant.price) * item.quantity for item in cart_items)
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
    total_price = sum(Decimal(item.variant.price) * item.quantity for item in cart_items)
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
    referred_users = []

    try:
        referral = Referral.objects.get(referrer=user)
        # Only call .all() if referral exists
        referred_users = referral.referred_users.all()
    except Referral.DoesNotExist:
        # User has no referral record yet
        referred_users = []

    context = {
        'referred_users': referred_users
    }
    return render(request, 'user/my_referrals.html', context)