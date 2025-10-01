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
def apply_coupon(request):
    print("Apply coupon view accessed.")
    if request.method == "POST" and request.user.is_authenticated:
        code = request.POST.get("coupon_code").strip()
        try:
            coupon = Coupon.objects.get(code__iexact=code, active=True)
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code")
            return redirect("select_payment")

        now = timezone.now()
        if not (coupon.valid_from <= now <= coupon.valid_to):
            messages.error(request, "This coupon is not valid now")
            return redirect("select_payment")

        # Check usage limit
        user_coupon, created = UserCoupon.objects.get_or_create(user=request.user, coupon=coupon)
        if user_coupon.used_count >= coupon.usage_limit:
            messages.error(request, "You have already used this coupon maximum times")
            return redirect("select_payment")

        # Optional: check min order amount
        cart_items = CartItems.objects.filter(user=request.user).select_related('variant')
        total_price = sum(Decimal(item.variant.price) * item.quantity for item in cart_items)
        if total_price < coupon.min_order_amount:
            print(coupon.min_order_amount)
            messages.error(request, f"Minimum order amount for this coupon is ₹{coupon.min_order_amount}")
            return redirect("select_payment")

        # Save coupon in session
        request.session["coupon_id"] = coupon.id
        print("Coupon saved in session.")
        messages.success(request, f'Coupon "{coupon.code}" applied successfully!')
        return redirect("select_payment")
    return redirect("select_payment")

#=-----------to remove coupon in user------
@login_required(login_url='login')
def remove_coupon(request): 
    if 'coupon_id' in request.session:
        del request.session['coupon_id']
        print("Coupon removed from session.")
        messages.success(request, "Coupon removed successfully.")
    return redirect('sellect_payment')