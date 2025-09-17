from django.shortcuts import render
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
from django.http import HttpResponse
from django.core.mail import send_mail

@login_required(login_url="login")
def orders(request):
    # --- GET search / filters from query params ---
    q = request.GET.get('q', '').strip()            # search box
    status_filter = request.GET.get('status', '').strip()  # optional: filter by status

    # --- base queryset: only user's orders ---
    orders_qs = Order.objects.filter(user=request.user)

    # --- apply search if provided (order_id, product name, status) ---
    if q:
        orders_qs = orders_qs.filter(
            Q(order_id__icontains=q) |
            Q(items__product_variant__product__name__icontains=q) |
            Q(status__icontains=q)
        ).distinct()

    # --- apply status filter if provided (exact match, case-insensitive) ---
    if status_filter:
        orders_qs = orders_qs.filter(status__iexact=status_filter)

    # --- prefetch related to avoid extra queries and order by date ---
    orders_qs = orders_qs.prefetch_related('items__product_variant__product').order_by('-order_date')

    # --- pagination ---
    paginator = Paginator(orders_qs, 4)   # 5 per page (change as needed)
    page_number = request.GET.get('page', 1)
    orders_page = paginator.get_page(page_number)

    # --- addresses for checkout/selection in template ---
    addresses = Address.objects.filter(user=request.user)

    context = {
        'orders': orders_page,
        'addresses': addresses,
        'q': q,
        'status_filter': status_filter,
    }
    return render(request, 'user/orders.html', context)

#------------------------------------------------------------------------------order details view------------------------------

@login_required(login_url="login")
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_id=order_number, user=request.user)
    order_items = order.items.select_related('product_variant__product')
    

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'user/order_details.html', context)

@login_required(login_url="login")
def cancel_order(request, order_id):
    print("Canceling order:", order_id)
    order = get_object_or_404(Order,id=order_id, user=request.user)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        # allow cancelling only when not already cancelled/delivered/returned depending on policy
        if order.status in ['cancelled', 'returned']:
            print("Order already cancelled:", order.order_id)
            messages.warning(request, 'Order cannot be cancelled.')
            return redirect('order_details', order_number=order.order_id)
        order.cancel_order(reason=reason)
        print("Order cancelled:", order.order_id)
        messages.success(request, 'Order cancelled successfully.')
        return redirect('order_details', order_number=order.order_id)
    return redirect('order_details', pk=order_id)



@login_required(login_url="login")
def cancel_item(request, item_id):
    # Fetch the OrderItem, ensuring it belongs to the logged-in user
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    
    if request.method == "POST":
        reason = request.POST.get("reason", "").strip() or None
        
        # Check if item is already cancelled
        if item.is_cancelled:
            print("Item already cancelled:", item.order.order_id)
            messages.info(request, "Item already cancelled.")
            return redirect("order_details", order_number=item.order.order_id)
        
        # Check if order is in a cancellable state
        if item.order.status not in ["pending", "confirmed"]:
            messages.error(request, "This item cannot be cancelled at this stage.")
            return redirect("order_details", order_number=item.order.order_id)
        
        # Attempt to cancel the item
        ok = item.cancel_item(reason=reason)
        if ok:
            # Recalculate order totals
            item.order.recalc_totals()
            # Check if all items are cancelled to update order status
            if all(i.is_cancelled for i in item.order.items.all()):
                item.order.status = "cancelled"
                item.order.cancelled_at = timezone.now()
                item.order.save()
            print("Item cancelled:", item.order.order_id)   
            messages.success(request, "Item cancelled and stock updated.")
        else:
            print("Failed to cancel item:", item.order.order_id)
            messages.error(request, "Could not cancel item.")
        
        return redirect("order_details", order_number=item.order.order_id)
    
    # Redirect to order detail page for GET requests
    return redirect("order_details", order_number=item.order.order_id)


@login_required(login_url="login")
def order_invoice_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    html = render_to_string("user/invoice.html", {"order": order, "user": request.user})
    # Option A: xhtml2pdf (simple)
    try:
        from xhtml2pdf import pisa
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