# admin views for WalkOn sales report
import calendar
from datetime import datetime, timedelta
from urllib import request
from django.utils import timezone
from decimal import Decimal
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.template.loader import render_to_string
import json
import time
import pandas as pd
from io import BytesIO
from django.shortcuts import render
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
from urllib3 import request
from django.views.decorators.cache import never_cache
from xhtml2pdf import pisa
from order.models import Order ,OrderItem  # avoid clash with razorpay
from django.http import JsonResponse
from django.utils.timezone import localdate
from django.db.models import Sum, Count
from datetime import timedelta
from django.db.models.functions import TruncMonth, TruncYear
from authentication.models import CustomUser as User
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, TruncYear
from datetime import timedelta
from order.models import Order, OrderItem
from wallet.models import WalletTransaction
from checkout.models import Payment
from django.template.loader import render_to_string


@never_cache
@staff_member_required(login_url="admin_login")
def admin_dashboard(request):
    today = timezone.localdate()

    # Paid / Valid orders today
    orders_today = Order.objects.filter(
        order_date__date=today,
        status__in=["placed", "delivered"]
    )

    total_sales_today = orders_today.aggregate(
        total=Sum("final_amount")
    )["total"] or 0

    total_orders_today = orders_today.count()

    products_sold_today = OrderItem.objects.filter(
        order__in=orders_today
    ).aggregate(
        total=Sum("quantity")
    )["total"] or 0

    new_customers_today = User.objects.filter(
        date_joined__date=today
    ).count()

    # Top 10 Products (all time)
    top_products = (
        OrderItem.objects.filter(
            order__status__in=["placed", "delivered"]
        )
        .values("product_variant__product__name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum("price")  # അല്ലെങ്കിൽ discounted_price / final_price ഉപയോഗിക്കാം
        )
        .order_by("-total_quantity")[:10]
    )

    # Top 5 Categories (all time)
    top_categories = (
        OrderItem.objects.filter(
            order__status__in=["placed", "delivered"]
        )
        .values("product_variant__product__category__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:5]
    )

    # Top 5 Brands (all time)
    top_brands = (
        OrderItem.objects.filter(
            order__status__in=["placed", "delivered"]
        )
        .values("product_variant__product__brand__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("-total_quantity")[:5]
    )

    context = {
        "total_sales_today": total_sales_today,
        "total_orders_today": total_orders_today,
        "products_sold_today": products_sold_today,
        "new_customers_today": new_customers_today,
        "top_products": top_products,
        "top_categories": top_categories,     
        "top_brands": top_brands,           
    }

    return render(request, "admin/dashboard.html", context)

# AJAX view for dashboard metrics (for real-time updates without page reload)
@staff_member_required(login_url="admin_login")
def admin_dashboard_data(request):
    now = timezone.now()
    last_24_hours = now - timedelta(hours=24)

    qs = Order.objects.filter(
        order_date__gte=last_24_hours,
        status__in=["placed", "delivered"]
    )

    return JsonResponse({
        "total_sales_today": qs.aggregate(total=Sum("final_amount"))["total"] or 0,
        "total_orders_today": qs.count(),
        "products_sold_today": OrderItem.objects.filter(order__in=qs).aggregate(total=Sum("quantity"))["total"] or 0,
        "new_customers_today": User.objects.filter(date_joined__gte=last_24_hours).count(),
    })
# ledger book

@staff_member_required(login_url='admin_login')
@never_cache
def download_ledger_excel(request):
    today = timezone.now().date()
    filter_type = request.GET.get('ledger_filter', 'monthly')
    start_date = request.GET.get('ledger_start')
    end_date = request.GET.get('ledger_end')

    # ── DATE RANGE ─────────────────────────────────────
    if filter_type == 'daily':
        start = end = today
    elif filter_type == 'weekly':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif filter_type == 'monthly':
        start = today.replace(day=1)
        end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    elif filter_type == 'yearly':
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
    elif filter_type == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        start = today.replace(day=1)
        end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    ledger_rows = []

    # ── ORDER PAYMENTS (Razorpay + Wallet) ──────────────
    order_payments = Payment.objects.filter(
        created_at__date__range=[start, end],
        payment_status='completed',
        order__isnull=False
    ).select_related('order')

    for p in order_payments:
        ledger_rows.append({
            'Date': p.created_at.date(),
            'Type': 'Income',
            'Amount': p.paid_amount,
            'Method': p.payment_method.upper(),
            'Description': f'Order {p.order.order_id}'
        })

    # ── COD DELIVERED ───────────────────────────────────
    cod_orders = Order.objects.filter(
        order_date__date__range=[start, end],
        status='delivered',
        payment_method='cod'
    )

    for o in cod_orders:
        ledger_rows.append({
            'Date': o.delivered_at.date() if o.delivered_at else o.order_date.date(),
            'Type': 'Income',
            'Amount': o.final_amount,
            'Method': 'COD',
            'Description': f'Order {o.order_id} - Delivered'
        })

    # ── REFUNDS (EXPENSE) ───────────────────────────────
    refunds = WalletTransaction.objects.filter(
        created_at__date__range=[start, end],
        purpose='refund'
    )

    for r in refunds:
        ledger_rows.append({
            'Date': r.created_at.date(),
            'Type': 'Expense',
            'Amount': r.amount,
            'Method': 'WALLET',
            'Description': r.description or 'Refund'
        })

    # ── EXCEL GENERATION ───────────────────────────────
    df = pd.DataFrame(ledger_rows).sort_values(by='Date', ascending=False)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ledger')

    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename=ledger_{start}_to_{end}.xlsx'
    )
    return response

    today = timezone.now().date()
    filter_type = request.GET.get('ledger_filter', 'monthly')
    start_date = request.GET.get('ledger_start')
    end_date = request.GET.get('ledger_end')

    # ── DATE RANGE ───────────────────────────────────────
    if filter_type == 'daily':
        start = end = today
    elif filter_type == 'weekly':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif filter_type == 'monthly':
        start = today.replace(day=1)
        end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    elif filter_type == 'yearly':
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
    elif filter_type == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        start = today.replace(day=1)
        end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    # ── INCOME ──────────────────────────────────────────

    # Razorpay + Wallet order payments (from Payment table)
    order_payments = Payment.objects.filter(
        created_at__date__range=[start, end],
        payment_status='completed',
        order__isnull=False
    ).select_related('order')

    razorpay_income = order_payments.filter(
        payment_method='razorpay'
    ).aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')

    wallet_income = order_payments.filter(
        payment_method='wallet'
    ).aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')

    # COD delivered
    cod_income = Order.objects.filter(
        order_date__date__range=[start, end],
        status='delivered',
        payment_method='cod'
    ).aggregate(total=Sum('final_amount'))['total'] or Decimal('0.00')

    total_income = razorpay_income + wallet_income + cod_income

    # ── EXPENSE (REFUNDS ONLY) ──────────────────────────
    refund_expense = WalletTransaction.objects.filter(
        created_at__date__range=[start, end],
        transaction_type='credit',
        purpose='refund'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    net_profit = total_income - refund_expense

    # ── LEDGER ROWS ─────────────────────────────────────
    ledger_rows = []
    print(order_payments,refund_expense)
    # Order payments (razorpay + wallet)
    for p in order_payments:
        ledger_rows.append({
            'date': p.created_at.date(),
            'type': 'Income',
            'amount': p.paid_amount,
            'method': p.payment_method.upper(),
            'desc': f'Order {p.order.order_id}'
        })

    # COD delivered orders
    for o in Order.objects.filter(
        order_date__date__range=[start, end],
        status='delivered',
        payment_method='cod'
    ):
        ledger_rows.append({
            'date': o.delivered_at.date() if o.delivered_at else o.order_date.date(),
            'type': 'Income',
            'amount': o.final_amount,
            'method': 'COD',
            'desc': f'Order {o.order_id} - Delivered'
        })

    # Refunds (expense)
    for r in WalletTransaction.objects.filter(
        created_at__date__range=[start, end],
        purpose='refund'
    ):
        ledger_rows.append({
            'date': r.created_at.date(),
            'type': 'Expense',
            'amount': r.amount,
            'method': 'WALLET',
            'desc': r.description or 'Refund'
        })
    print(order_payments,)

    ledger_rows.sort(key=lambda x: x['date'], reverse=True)

    context = {
        'filter_type': filter_type,
        'start_date': start,
        'end_date': end,
        'total_income': total_income,
        'total_expense': refund_expense,
        'net_profit': net_profit,
        'ledger_rows': ledger_rows[:100],
    }

    # ── EXCEL DOWNLOAD ──────────────────────────────────
    if request.GET.get('ledger_download') == 'excel':
        df = pd.DataFrame(ledger_rows)
        df.rename(columns={
            'date': 'Date',
            'type': 'Type',
            'amount': 'Amount',
            'method': 'Method',
            'desc': 'Description'
        }, inplace=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)

        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename=ledger_{start}_to_{end}.xlsx'
        )
        return response

    return render(request, 'admin/ledger_book.html', context)

#Sales chart data (monthly / yearly)
@staff_member_required(login_url="admin_login")
def sales_chart_data(request):
    filter_type = request.GET.get("filter", "monthly")

    qs = Order.objects.filter(status__in=["placed", "delivered"])

    if filter_type == "yearly":
        data = (
            qs.annotate(year=TruncYear("order_date"))
            .values("year")
            .annotate(total=Sum("final_amount"))
            .order_by("year")
        )
    else:
        data = (
            qs.annotate(month=TruncMonth("order_date"))
            .values("month")
            .annotate(total=Sum("final_amount"))
            .order_by("month")
        )

    # JSON-ന് safe=False വേണ്ട, list(data) മതി
    return JsonResponse(list(data), safe=False)


# ------------------------- Sales Report View ------------------------ #
VALID_STATUSES = [
    'confirmed',
    'shipped',
    'out for delivery',
    'delivered',
    'partially_returned'
]

@staff_member_required(login_url='admin_login')
@never_cache
def sales_report_view(request):
    today = timezone.localdate()
    filter_type = request.GET.get('filter', 'daily')  # default daily
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_filter = request.GET.get('order_status', 'all')

    # Date range logic (same as before)
    if filter_type == 'daily':
        start = today
        end = today
    elif filter_type == 'weekly':
        start = today - timedelta(days=6)
        end = start + timedelta(days=6)
    elif filter_type == 'monthly':
        start = today.replace(day=1)
        last_day = calendar.monthrange(start.year, start.month)[1] # get last day of month
        end = start.replace(day=last_day)
    elif filter_type == 'yearly':
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
    elif filter_type == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        start = today
        end = today

    # Queryset
    orders = Order.objects.filter(
        order_date__date__range=[start,end]
    )
    if status_filter != 'all': # apply status filter if not 'all' exclude cancelled ,returned,failed,etc
        orders = orders.filter(status=status_filter)
    else:
        orders = orders.filter(status__in=VALID_STATUSES)

    sales_orders = orders.filter(status__in=['delivered','partially_returned']) # only consider these for sales calculations/delevered/partially returned

    # Aggregations
    total_orders = orders.count()
    total_amount = orders.aggregate(total=Sum('final_amount'))['total'] or Decimal('0.00')
    total_discount = orders.aggregate(discount=Sum('discount_amount'))['discount'] or Decimal('0.00')
    coupon_used = orders.filter(coupon__isnull=False).count()
    coupon_discount = orders.filter(coupon__isnull=False).aggregate(d=Sum('discount_amount'))['d'] or Decimal('0.00')

    print("FILTER:", filter_type)
    print("START:", start_date)
    print("END:", end_date)
    print("STATUS:", status_filter)
    print("COUNT:", orders.count())


    context = {
        'filter_type': filter_type,
        'start_date': start,
        'end_date': end,
        'order_status_filter': status_filter,
        'total_orders': total_orders,
        'total_amount': total_amount,
        'total_discount': total_discount,
        'coupon_used': coupon_used,
        'coupon_discount': coupon_discount,
        'orders': orders.order_by('-order_date')[:50],
    }

    # 2. AJAX Partial Update (filter apply without reload)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        print("AJAX request received")
        print("Filter type:", filter_type)
        print("Status filter:", status_filter)
        print("Date range:", start, "to", end)
        print("Orders count in response:", orders.count())
        print("Order IDs:", list(orders.values_list('order_id', flat=True)[:10]))  # first 10
        return render(request, 'admin/_sales_report_data.html', context)
    # ---------------------- PDF Download ---------------------- #
    if request.GET.get('download') == 'pdf':
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start}_to_{end}.pdf"'
        pisa.CreatePDF(
            render_to_string('admin/sales_report_pdf.html', context),
            dest=response
        )
        return response

    # ---------------------- Excel Download ---------------------- #
    if request.GET.get('download') == 'excel':
        data = {
            'Order ID': [o.order_id for o in orders],
            'Date': [o.order_date.date() for o in orders],
            'User': [o.user.username for o in orders],
            'Total': [float(o.final_amount) for o in orders],
            'Discount': [float(o.discount_amount) for o in orders],
            'Status': [o.get_status_display() for o in orders],
            'Payment Method': [o.payment_method for o in orders],
        }
        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sales')
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="sales_report_{start}_to_{end}.xlsx"'
        return response

    # 3. Normal page load
    return render(request, 'admin/sales_report.html', context)

