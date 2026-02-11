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
#------------------------------------------------------------------------------cancel order view------------------------------

@login_required(login_url="login")
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    redirect_to = (
        request.POST.get('next') or
        request.META.get('HTTP_REFERER') or
        'orders'
    )

    if request.method != 'POST':
        return redirect(redirect_to)

    reason = request.POST.get('reason', '').strip()

    if order.status in ['cancelled', 'returned']:
        messages.warning(request, 'This order is already cancelled or returned.')
        return redirect(redirect_to)

    try:
        with transaction.atomic():
            # for refund calculation
            refund_amount = Decimal(str(order.final_amount))  # Save original final amount
            print(f"[DEBUG] Original final amount before cancel: ₹{refund_amount}")

            success = order.cancel_order(reason=reason)
            if not success:
                raise ValueError("Cancel failed in model method")
            
            # REFUND LOGIC: COD check
            payment_method = (order.payment_method or "").lower()
            if payment_method == "cod":
                refund_amount = Decimal("0.00")
                print("[DEBUG] COD order - no refund applicable")

            # Refund logic (use original final amount)
            if refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                print(f" Wallet balance before refund: ₹{wallet.balance}")

                wallet.balance += refund_amount
                wallet.save(update_fields=['balance'])
                wallet.refresh_from_db()
                print(f"Wallet balance after refund: ₹{wallet.balance}")

                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type="credit",
                    purpose="refund",
                    description=f"Full order cancelled refund - Order #{order.order_id}"
                )
                print("[DEBUG] Refund transaction created")
            else:
                print("[DEBUG] No refund needed (amount <= 0)")
                messages.info(request, 'No refund amount to process.')

            messages.success(
                request,
                f'Order #{order.order_id} successfully cancelled. '
                f'₹{refund_amount:.2f} credited to your wallet.'
            )

            return redirect(redirect_to)

    except Exception as e:
        import traceback
        print("=== CANCEL ORDER ERROR ===")
        print(f"Order ID: {order.order_id}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        traceback.print_exc()
        print("========================")

        messages.error(request, 'Cancellation failed. Please check server logs or contact support.')
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

    if request.method != "POST":
        return redirect(redirect_to)

    reason = request.POST.get("reason", "").strip() or None  # for logging purpose

    if item.is_cancelled:
        messages.info(request, "Item already cancelled.")
        return redirect(redirect_to)

    order = item.order

    if order.status not in ["pending", "confirmed"]:
        messages.error(request, "This item cannot be cancelled now.")
        return redirect(redirect_to)

    try:
        with transaction.atomic():
            # ORIGINAL FINAL AMOUNT SAVE (refund-calculation purpose)
            original_final = Decimal(str(order.final_amount or '0.00'))

            # COD check → refund 0 force 
            refund_amount = Decimal('0.00')
            payment_method = (order.payment_method or "").lower()
            is_cod = (payment_method == "cod")
            print(f"[DEBUG] Payment method: {payment_method} | is_cod: {is_cod}")

            if is_cod:
                print("[DEBUG] COD order - no refund on item cancel")
                messages.info(request, "COD order - no refund applicable on item cancel.")
                reason = reason or "Cancelled - COD order"
            else:
                
                print("[DEBUG] Non-COD order - calculating proportional refund")

            # Item cancel + restock 
            item.is_cancelled = True
            item.cancel_reason = reason
            item.cancelled_at = timezone.now()
            item.save()

            product = item.product_variant.product
            product.stock = F("stock") + item.quantity
            product.save(update_fields=["stock"])

            # Recalculate totals (coupon redistribution) → amount change happens here
            order.recalc_totals()

            # Refund logic: COD=0 else difference calculation
            if not is_cod:
                refund_amount = original_final - Decimal(str(order.final_amount or '0.00'))
                refund_amount = max(Decimal("0.00"), refund_amount)

            # Refund process (COD-ന് skip)
            if refund_amount > 0:
                wallet, _ = Wallet.objects.get_or_create(user=request.user)
                wallet.balance += refund_amount
                wallet.save(update_fields=['balance'])

                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type="credit",
                    purpose="refund",
                    description=f"Refund for cancelled item ({item.product_variant.product.name}) in order {order.order_id}"
                )
            else:
                print("[DEBUG] No refund processed (COD or zero amount)")

            # All items cancelled ?
            if all(i.is_cancelled for i in order.items.all()):
                order.status = "cancelled"
                order.cancelled_at = timezone.now()
                order.save()

            messages.success(
                request,
                f"Item cancelled successfully. "
                f"{'₹' + str(refund_amount.quantize(Decimal('0.01'))) + ' refunded to wallet.' if refund_amount > 0 else 'No refund applicable (COD order).'}"
            )

            return redirect(redirect_to)

    except Exception as e:
        print(f"[ERROR] Cancel item failed: {type(e).__name__}: {str(e)}")
        messages.error(request, 'Item cancellation failed. Please try again or contact support.')
        return redirect(redirect_to)
    #--------------------------------------------------------------------request return item---------

#-----------------------------request return item------------------------------
@login_required(login_url="login")
def request_return_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    order = item.order

    #  order should be delivered or partially returned to request return
    if order.status not in ["delivered", "partially_returned"]:
        messages.error(request, "This item cannot be returned at this time.")
        return redirect('order_details', order_number=order.order_id)
    #  item should not be already returned or cancelled
    if item.is_returned or item.is_cancelled:
        messages.error(request, "This item is already returned or cancelled.")
        return redirect('order_details', order_number=order.order_id)
    #
    if request.method == "POST":     # POST request to submit return request
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
        # Order should be delivered or partially returned

        if order.status not in ["delivered", "partially_returned"]:
            messages.error(request, "This order cannot be returned at this time.")
            return redirect('order_details', order_number=order.order_id)
        # Prevent duplicate request
        if ReturnRequest.objects.filter(order=order, status="requested", request_type="order").exists():
            messages.info(request, "Return request already submitted for this order.")
            return redirect('order_details', order_number=order.order_id)
        # Create return request
        reason = request.POST.get("reason", "").strip() or None

        if not reason:
            messages.error(request, "Please provide a reason for return.")
            return redirect('order_details', order_number=order.order_id)

        rr = ReturnRequest.objects.create(
            request_type="order",
            order=order,
            order_item=None,
            status="requested",
            requested_by=request.user,
            reason=reason,
        )

        return redirect('order_details', order_number=order.order_id)
    return redirect('order_details', order_number=order.order_id)
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
    total=order.total_amount-order.discount_amount
    context = {
        'order': order,
        'order_items': order_items,
        'total': total,
    }
    return render(request, 'admin/admin_order_details.html', context)


@staff_member_required(login_url="admin_login")
def admin_order_action(request, order_number):
    order = get_object_or_404(Order, order_id=order_number)

    action = request.POST.get("action")
    item_id = request.POST.get("item_id")
    # UPDATE ORDER STATUS
    if order.status=="delivered" and action == "update_status":
        messages.error(request, "Delivered orders cannot have their status changed.")
        return redirect("admin_order_details", order.order_id)
    if order.status=="cancelled" or order.status=="returned" and action == "update_status":
        messages.error(request, "Cancelled or returned orders cannot have their status changed.")
        return redirect("admin_order_details", order.order_id)

    if action == "update_status":
        new_status = request.POST.get("status")
        order.status = new_status
        order.save(update_fields=['status'])
        messages.success(request, "Order status updated successfully.")
        return redirect("admin_order_details", order.order_id)

    # APPROVE RETURN (single item return)
    if action == "approve_return": #this is from admin return request list
        if not item_id:       # item_id is required
            messages.error(request, "Item ID missing.")
            return redirect("admin_order_details", order.order_id)

        item = get_object_or_404(OrderItem, id=item_id, order=order)  
        user = order.user

        if item.admin_refunded:
            messages.info(request, "Refund already processed for this item.")
            return redirect("admin_order_details", order.order_id)

        if item.is_returned:  # admin already marked as returned
            messages.info(request, "Item already marked as returned.")
            return redirect("admin_order_details", order.order_id)

        try:
            with transaction.atomic():
                # 1. Original final amount save 
                original_final = order.final_amount.quantize(Decimal('0.01'))

                # 2. Item- returned + refunded  + restock
                item.is_returned = True
                item.admin_refunded = True
                item.returned_at = timezone.now()  # optional, if you have this field
                item.save(update_fields=['is_returned', 'admin_refunded', 'returned_at'])

                # Restock product
                product = item.product_variant.product
                product.stock = F("stock") + item.quantity
                product.save(update_fields=["stock"])

                # 3. Recalculate totals → coupon redistribution 
                order.recalc_totals()

                # 4. Refund = original final - new final
                refund_amount = original_final - order.final_amount
                refund_amount = max(Decimal('0.00'), refund_amount.quantize(Decimal('0.01')))

                if refund_amount > 0:
                    wallet, _ = Wallet.objects.get_or_create(user=user)
                    wallet.balance += refund_amount
                    wallet.save(update_fields=['balance'])

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=refund_amount,
                        transaction_type="credit",
                        purpose="refund",
                        description=f"Admin approved return refund for item {item.product_variant.product.name} (Order: {order.order_id})"
                    )

                # 5. Order status update
                remaining_items = order.items.filter(is_returned=False, is_cancelled=False)
                if remaining_items.exists():
                    order.status = "partially_returned"
                else:
                    order.status = "returned"
                order.save(update_fields=['status'])

                messages.success(
                    request,
                    f"Return approved! ₹{refund_amount:.2f} refunded to user's wallet."
                )
                print(f"Refund approved: {refund_amount} | New status: {order.status}")

        except Exception as e:
            print(f"Approve return error: {str(e)}")
            messages.error(request, "Error processing return approval. Please try again.")
        
        return redirect("admin_order_details", order.order_id)

    else:
        messages.error(request, "Invalid action requested.")
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

    if rr.status != "requested":
        messages.info(request, "This return request is already processed.")
        return redirect("admin_return_requests")

    if request.method != "POST":
        return redirect("admin_return_requests")

    action = request.POST.get("action")  # approve / reject

    # ===================== APPROVE =====================
    if action == "approve":
        try:
            # Save original final amount (before return)
            original_final = order.final_amount.quantize(Decimal("0.01"))
            total_refund = Decimal("0.00")

            # ---------- SINGLE ITEM RETURN ----------
            if rr.request_type == "item" and rr.order_item:
                item = rr.order_item

                if item.admin_refunded or item.is_returned:
                    messages.info(request, "Item already processed.")
                    return redirect("admin_return_requests")

                # Mark returned
                item.is_returned = True
                item.admin_refunded = True
                item.returned_at = timezone.now()
                item.save()

                # Restock
                product = item.product_variant.product
                product.stock = F("stock") + item.quantity
                product.save(update_fields=["stock"])

            # ---------- FULL ORDER RETURN ----------
            elif rr.request_type == "order":
                for item in order.items.filter(is_returned=False, is_cancelled=False):
                    item.is_returned = True
                    item.admin_refunded = True
                    item.returned_at = timezone.now()
                    item.save()

                    # Restock
                    product = item.product_variant.product
                    product.stock = F("stock") + item.quantity
                    product.save(update_fields=["stock"])

            # ---------- RECALCULATE TOTALS ----------
            order.recalc_totals()

            # ---------- REFUND = DIFFERENCE ----------
            total_refund = original_final - order.final_amount
            total_refund = max(Decimal("0.00"), total_refund.quantize(Decimal("0.01")))

            # ---------- WALLET REFUND ----------
            if total_refund > 0:
                wallet, _ = Wallet.objects.get_or_create(user=user)
                wallet.balance += total_refund
                wallet.save(update_fields=["balance"])

                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=total_refund,
                    transaction_type="credit",
                    purpose="refund",
                    description=f"Admin approved {rr.request_type} return refund (Order: {order.order_id})"
                )

            # ---------- UPDATE ORDER STATUS ----------
            remaining = order.items.filter(is_returned=False, is_cancelled=False)
            order.status = "partially_returned" if remaining.exists() else "returned"
            order.save(update_fields=["status"])

            # ---------- UPDATE RETURN REQUEST ----------
            rr.status = "approved"
            rr.processed = True
            rr.processed_at = timezone.now()
            rr.processed_by = request.user
            rr.refund_amount = total_refund
            rr.notes = f"Approved by admin. Refunded ₹{total_refund:.2f}"
            rr.save()

            messages.success(
                request,
                f"Return approved! ₹{total_refund:.2f} refunded to wallet."
            )
            return redirect("admin_return_requests")

        except Exception as e:
            print(f"[ADMIN RETURN ERROR] {type(e).__name__}: {str(e)}")
            messages.error(request, "Error approving return. Please try again.")
            return redirect("admin_return_requests")

    # ===================== REJECT =====================
    elif action == "reject":
        rr.status = "rejected"
        rr.processed = True
        rr.processed_at = timezone.now()
        rr.processed_by = request.user
        rr.notes = "Rejected by admin"
        rr.save()

        messages.error(request, "Return request rejected.")
        return redirect("admin_return_requests")

    return redirect("admin_return_requests")
#===================== ADMIN RETURN REQUEST DETAIL VIEW =====================
@staff_member_required(login_url="admin_login")
def admin_return_request_details(request, request_id):
    rr = get_object_or_404(ReturnRequest, id=request_id)
    return render(request, "admin/return_request_details.html", {"request": rr})