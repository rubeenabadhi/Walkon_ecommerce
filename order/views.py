from django.shortcuts import render
from review.forms import ReviewForm
from .models import *
from django.contrib.auth.decorators import login_required
from address.models import Address
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.db.models import F, Sum, DecimalField
from wallet.models import Wallet, WalletTransaction
from xhtml2pdf import pisa
from review.models import Review


#========================================================================USER ORDER VIEW===============================================
@login_required(login_url="login")
def orders(request):
    # 1️⃣ Search and filter parameters
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    # 2️⃣ Base queryset — all orders of current logged-in user
    orders_qs = Order.objects.filter(user=request.user)

    # 3️⃣ Apply search query if user typed anything
    if q:
        orders_qs = orders_qs.filter(
            Q(order_id__icontains=q) |
            Q(items__product_variant__product__name__icontains=q) |
            Q(status__icontains=q) |
            Q(order_date__icontains=q) |
            Q(payment_method__icontains=q)
        ).distinct()

    # 4️⃣ Apply status filter if selected from dropdown
    if status_filter:
        orders_qs = orders_qs.filter(status__iexact=status_filter)

    # 5️⃣ Prefetch related objects to reduce DB hits (for performance)
    orders_qs = (
        orders_qs
        .prefetch_related('items__product_variant__product', 'payment')
        .order_by('-order_date')
    )

    # 6️⃣ Pagination setup (4 orders per page)
    paginator = Paginator(orders_qs, 4)
    page_number = request.GET.get('page', 1)
    orders_page = paginator.get_page(page_number)

    # 7️⃣ Totals across all orders (for summary display)
    totals = orders_qs.annotate(
        # Calculate total of each order's item = price × quantity
        item_total=F('items__price') * F('items__quantity')
    ).aggregate(
        # Sum all item totals (exclude cancelled items)
        total_spent=Sum(
            'item_total',
            filter=Q(items__is_cancelled=False),
            output_field=DecimalField()
        ),
        # Sum of quantities of all ordered products
        total_products=Sum(
            'items__quantity',
            filter=Q(items__is_cancelled=False)
        )
    )

    # 8️⃣ Ensure default values if totals are None
    total_spent = totals['total_spent'] or Decimal('0.00')
    total_products = totals['total_products'] or 0

    # 9️⃣ Prepare context for template rendering
    context = {
        'orders': orders_page,
        'addresses': Address.objects.filter(user=request.user),
        'q': q,
        'status_filter': status_filter,
        'total_spent': total_spent,
        'total_products': total_products,
    }

    # 🔟 Render the template
    return render(request, 'user/orders.html', context)

#------------------------------------------------------------------------------order details view------------------------------

@login_required(login_url="login")
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_id=order_number, user=request.user)
    order_items = order.items.select_related('product_variant__product')

    # Collect products that already have reviews
    reviewed_products = set(
        Review.objects.filter(user=request.user).values_list('product_id', flat=True)
    )

    review_form = ReviewForm()

    # 🔥 Correct: Create a dictionary of existing reviews for each product
    existing_reviews = {}

    for item in order.items.all():
        product = item.product_variant.product
        existing_review = Review.objects.filter(
            user=request.user,
            product=product
        ).first()

        existing_reviews[product.id] = existing_review  # <-- store it properly

    context = {
        'order': order,
        'order_items': order_items,
        'reviewed_products': reviewed_products,
        'review_form': review_form,
        'existing_reviews': existing_reviews,   
    }

    return render(request, 'user/order_details.html', context)

@login_required(login_url="login")
def cancel_order(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Safe redirect
    redirect_to = (
        request.POST.get('next') or
        request.META.get('HTTP_REFERER') or
        'orders'
    )

    if request.method == 'POST':

        reason = request.POST.get('reason', '').strip()

        # Prevent double cancel
        if order.status in ['cancelled', 'returned']:
            messages.warning(request, 'Order cannot be cancelled.')
            return redirect(redirect_to)

        # Cancel all items
        order.cancel_order(reason=reason)

        # REFUND ------------------------------------------------------
        refund_amount = order.final_amount
        if refund_amount < 0:
            refund_amount = 0

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.balance += refund_amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=refund_amount,
            transaction_type="credit",
            description=f"Refund for cancelled order {order.order_id}"
        )

        messages.success(
            request,
            f'Order cancelled and ₹{refund_amount} refunded to wallet.'
        )
        return redirect(redirect_to)

    return redirect(redirect_to)

#------------------------------------------------------------------------------cancel item view------------------------------

@login_required(login_url="login")
def cancel_item(request, item_id):

    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    redirect_to = (
        request.POST.get('next') or
        request.META.get('HTTP_REFERER') or
        '/orders/'
    )

    if request.method == "POST":

        reason = request.POST.get("reason", "").strip() or None

        # Already cancelled
        if item.is_cancelled:
            messages.info(request, "Item already cancelled.")
            return redirect(redirect_to)

        order = item.order

        # Only pending/confirmed orders can be cancelled
        if order.status not in ["pending", "confirmed"]:
            messages.error(request, "This item cannot be cancelled now.")
            return redirect(redirect_to)

        # -------------------------------------------------------------
        # Step 1: Cancel item
        # -------------------------------------------------------------
        item.is_cancelled = True
        item.cancel_reason = reason
        item.cancelled_at = timezone.now()
        item.save()

        # -------------------------------------------------------------
        # Step 2: Refund calculation + coupon redistribution
        # -------------------------------------------------------------

        refund_amount = item.total_price
        coupon = order.coupon

        if coupon:
            # Total of all items (cancelled + not cancelled)
            all_items = order.items.all()
            total_original = sum(i.total_price for i in all_items)

            # Determine full discount amount
            if coupon.discount_type == "amount":
                total_discount = Decimal(coupon.discount_value)

            elif coupon.discount_type == "percentage":
                total_discount = (Decimal(coupon.discount_value) / 100) * total_original

            else:
                total_discount = Decimal("0.00")

            # Proportional discount share for THIS item
            item_discount_share = (item.total_price / total_original) * total_discount

            # Subtract item’s discount share
            refund_amount -= item_discount_share

            # Ensure no negative refund
            refund_amount = max(Decimal("0.00"), refund_amount)

        # -------------------------------------------------------------
        # Step 3: Refund to Wallet
        # -------------------------------------------------------------
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.balance += refund_amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=refund_amount,
            transaction_type="credit",
            description=f"Refund for cancelled item ({item.product_variant.product.name}) in order {order.order_id}"
        )

        # -------------------------------------------------------------
        # Step 4: Recalculate order totals
        # -------------------------------------------------------------
        order.recalc_totals()

        # If ALL items cancelled → cancel order fully
        if all(i.is_cancelled for i in order.items.all()):
            order.status = "cancelled"
            order.cancelled_at = timezone.now()
            order.save()

        messages.success(
            request,
            f"Item cancelled and ₹{refund_amount:.2f} refunded to wallet."
        )
        return redirect(redirect_to)

    return redirect(redirect_to)


#--------------------------------------------------------------------request return item---------
@login_required(login_url="login")
def request_return_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = item.order

    # Order delivered ആയിരിക്കണം അല്ലെങ്കിൽ partially returned ആയിരിക്കാം
    if order.status not in ["delivered", "partially_returned"]:
        messages.error(request, "This item cannot be returned at this time.")
        return redirect('order_details', order_number=order.order_id)

    if item.is_returned or item.is_cancelled:
        messages.error(request, "This item is already returned or cancelled.")
        return redirect('order_details', order_number=order.order_id)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Please provide a reason for return.")
            return redirect('order_details', order_number=order.order_id)

        # Prevent duplicate request
        if ReturnRequest.objects.filter(order_item=item, status="requested").exists():
            messages.info(request, "Return request already submitted for this item.")
            return redirect('order_details', order_number=order.order_id)

        # Create return request
        ReturnRequest.objects.create(
            request_type="item",
            order=order,
            order_item=item,
            status="requested",
            requested_by=request.user,
            reason=reason,
        )

        messages.success(request, f"Return request for '{item.product_variant.product.name}' submitted successfully!")
        return redirect('order_details', order_number=order.order_id)

    return redirect('order_details', order_number=order.order_id)

#-----------------------------request return order------------------------------
@login_required(login_url="login")
def request_return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == "POST":
        if order.status in ["Return Requested", "returned"]:
            return JsonResponse({"error": "Return already requested or completed"}, status=400)

        reason = request.POST.get("reason", "").strip() or None

        rr = ReturnRequest.objects.create(
            request_type="order",
            order=order,
            order_item=None,
            status="requested",
            requested_by=request.user,
            reason=reason,
        )

        return JsonResponse({"message": "Return request submitted successfully"})
    return JsonResponse({"error": "Invalid method"}, status=405) 
#------------------------------------------------------------------------------invoice view------------------------------

@login_required(login_url="login")
def order_invoice_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    html = render_to_string("user/invoice.html", {"order": order, "user": request.user})
    # Option A: xhtml2pdf (simple)
    try:
        
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="invoice-{order.order_id}.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            messages.error(request, "Error generating PDF.")
            return redirect("orders:detail", pk=order.id)
        return response
    except Exception:
        messages.error(request, "PDF library not installed. Install xhtml2pdf or use WeasyPrint.")
        return redirect("orders:detail", pk=order.id)
    
#======================================================================ADMIN VIEWS=========================================================

#===================== ADMIN ORDER LIST VIEW =====================
from django.contrib.admin.views.decorators import staff_member_required
@staff_member_required(login_url="admin_login")
def admin_orders(request):
    # --- GET search / filters from query params ---
    q = request.GET.get('q', '').strip()            # search box
    status_filter = request.GET.get('status', '').strip()  # optional: filter by status 
    # --- base queryset: all orders ---
    orders_qs = Order.objects.all()
    # --- apply search if provided (order_id, product name, status) ---
    if q:
        orders_qs = orders_qs.filter(
            Q(user__username__icontains=q) |
            Q(order_id__icontains=q) |
            Q(items__product_variant__product__name__icontains=q) |
            Q(status__icontains=q) |
            Q(order_date__icontains=q)
        ).distinct()
    # --- apply status filter if provided --- (exact match, case-insensitive) ---
    if status_filter:
        orders_qs = orders_qs.filter(status__iexact=status_filter)
    # --- prefetch related to avoid extra queries and order by date ---
    orders = orders_qs.prefetch_related('items__product_variant__product').order_by('-order_date')
    # --- pagination ---
    paginator = Paginator(orders, 20)   # 5 per page (change as needed)
    page_number = request.GET.get('page', 1)
    orders_page = paginator.get_page(page_number)
    # --- context ---
    context = {
        'orders': orders_page,
        'q': q,
        'status_filter': status_filter,
    }
    return render(request, 'admin/admin_orders.html', context)    
    
#===================== ADMIN ORDER DETAIL VIEW =====================
@staff_member_required(login_url="admin_login")
def admin_order_detail(request, order_number):
    order = get_object_or_404(Order, order_id=order_number)
    order_items = order.items.select_related('product_variant__product')
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'admin/admin_order_details.html', context)


@staff_member_required(login_url="admin_login")
def admin_order_action(request, order_number):
    order = get_object_or_404(Order, order_id=order_number)

    action = request.POST.get("action")
    item_id = request.POST.get("item_id")

    # 1. UPDATE ORDER STATUS
    # --------------------------------------------
    if action == "update_status":
        new_status = request.POST.get("status")
        order.status = new_status
        order.save()
        print(order.status)

        messages.success(request, "Order status updated successfully.")
        return redirect("admin_order_details", order.order_id)

    # 2. APPROVE RETURN ITEM
    # --------------------------------------------
    if action == "approve_return":
        item = get_object_or_404(OrderItem, id=item_id)
        user = order.user

        if item.admin_refunded:
            messages.info(request, "Refund already processed.")
            return redirect("admin_order_details", order.order_id)

        refund_amount = item.total_price
        coupon = order.coupon

        if coupon:
            all_items = order.items.all()
            total_original = sum(i.total_price for i in all_items)

            if coupon.discount_type == "amount":
                total_discount = Decimal(coupon.discount_value)
            elif coupon.discount_type == "percentage":
                total_discount = (Decimal(coupon.discount_value) / 100) * total_original
            else:
                total_discount = Decimal("0.00")

            item_discount_share = (item.total_price / total_original) * total_discount
            refund_amount -= item_discount_share
            refund_amount = max(Decimal("0.00"), refund_amount)

        wallet, _ = Wallet.objects.get_or_create(user=user)
        wallet.balance += refund_amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=refund_amount,
            transaction_type="credit",
            description=f"Refund for returned item {item.product_variant.product.name}"
        )

        item.admin_refunded = True
        item.save()

        remaining_items = order.items.filter(is_returned=False, is_cancelled=False)
        order.status = "partially_returned" if remaining_items.exists() else "returned"
        order.save()

        print("Refund approved and credited successfully.",refund_amount)
        print(order.status)
        messages.success(request, "Refund approved and credited successfully.")
        return redirect("admin_order_details", order.order_id)

    else:
        messages.error(request, "Invalid admin action.")
        print("Invalid admin action.")
        return redirect("admin_order_details", order.order_id)
    


#===================== ADMIN RETURN REQUEST VIEW =====================
@staff_member_required(login_url="admin_login")
def admin_return_requests_list(request):
    return_requests = ReturnRequest.objects.select_related(
            "order",
            "order_item",
            "requested_by"
            ).filter(status="requested").order_by("-id")

    print(return_requests)    
    # render to a template with approve/reject buttons
    return render(request, "admin/return_requests_list.html", {"requests": return_requests})

#-----------------------------PROCESS RETURN REQUEST VIEW------------------------------
@staff_member_required(login_url="admin_login")
@transaction.atomic
def admin_process_return(request, request_id):
    rr = get_object_or_404(ReturnRequest, id=request_id)
    order = rr.order
    user = order.user

    # Already processed?
    if rr.status != "requested":
        messages.info(request, "This return request is already processed.")
        return redirect("admin_return_requests")

    if request.method == "POST":
        action = request.POST.get("action")  # approve or reject

        # Helper function - coupon proportional refund calculate ചെയ്യാൻ
        def calculate_refund_amount(item):
            items = list(order.items.all())
            if not items:
                return Decimal("0.00")

            total_original = sum(i.total_price for i in items) or Decimal("1")
            discount_share = Decimal("0.00")

            if order.coupon:
                if order.coupon.discount_type == "amount":
                    total_discount = Decimal(order.coupon.discount_value)
                elif order.coupon.discount_type == "percentage":
                    total_discount = (Decimal(order.coupon.discount_value) / 100) * total_original
                else:
                    total_discount = Decimal("0.00")

                discount_share = (item.total_price / total_original) * total_discount

            refund = item.total_price - discount_share
            return max(Decimal("0.00"), refund.quantize(Decimal("0.01")))

        total_refund = Decimal("0.00")

        # APPROVE RETURN
        if action == "approve":

            # ====== SINGLE ITEM RETURN ======
            if rr.request_type == "item":
                item = rr.order_item  # ഇവിടെ മാറ്റി! (item → order_item)

                if item.admin_refunded:
                    messages.info(request, "This item is already refunded.")
                    return redirect("admin_return_requests")

                refund = calculate_refund_amount(item)
                total_refund += refund

                # Refund to wallet
                wallet, _ = Wallet.objects.get_or_create(user=user)
                wallet.balance += refund
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund,
                    transaction_type="credit",
                    description=f"Return approved - {item.product_variant.product.name} (Order: {order.order_id})"
                )

                # Mark as returned & refunded
                item.is_returned = True
                item.admin_refunded = True
                item.save()

                # Update order status
                remaining = order.items.filter(is_returned=False, is_cancelled=False)
                if remaining.exists():
                    order.status = "partially_returned"
                else:
                    order.status = "returned"
                order.save()

            # ====== FULL ORDER RETURN ======
            elif rr.request_type == "order":
                for item in order.items.all():
                    if item.is_cancelled or item.admin_refunded:
                        continue

                    refund = calculate_refund_amount(item)
                    total_refund += refund

                    # Refund
                    wallet, _ = Wallet.objects.get_or_create(user=user)
                    wallet.balance += refund
                    wallet.save()

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=refund,
                        transaction_type="credit",
                        description=f"Full order return - {order.order_id}"
                    )

                    item.is_returned = True
                    item.admin_refunded = True
                    item.save()

                    # Restock (optional)
                    product = item.product_variant.product
                    product.stock = models.F("stock") + item.quantity
                    product.save()

                order.status = "returned"
                order.save()

            # Update ReturnRequest
            rr.status = "approved"
            rr.processed = True
            rr.processed_at = timezone.now()
            rr.processed_by = request.user
            rr.refund_amount = total_refund
            rr.notes = f"Approved by admin. Refunded ₹{total_refund:.2f}"
            rr.save()

            messages.success(request, f"Return approved! ₹{total_refund:.2f} refunded to wallet.")
            return redirect("admin_return_requests")

        # REJECT RETURN
        elif action == "reject":
            rr.status = "rejected"
            rr.processed = True
            rr.processed_at = timezone.now()
            rr.note = "Rejected by admin"
            rr.save()
            messages.error(request, "Return request rejected.")
            return redirect("admin_return_requests")

    return redirect("admin_return_requests")
#--------------------------------------------RETURN REQUEST DETAILS VIEW----------------------------------------------
@staff_member_required(login_url="admin_login")
def admin_return_request_details(request, request_id):
    rr = get_object_or_404(ReturnRequest, id=request_id)
    return render(request, "admin/return_request_details.html", {"request": rr})