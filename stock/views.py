from django.shortcuts import render
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from product.models import Product
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

@staff_member_required(login_url='admin_login')
def stock_management(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')

    variants = Product.objects.all()
    if query:
        variants = variants.filter(
            Q(product__name__icontains=query) 
            
        )
  
    if status_filter == 'low':
        variants = variants.filter(stock__lte=5, stock__gt=0)
    elif status_filter == 'out':
        variants = variants.filter(stock=0)
    elif status_filter == 'in':
        variants = variants.filter(stock__gt=5)

    context = {
        'variants': variants.order_by('stock'),
        'query': query,
        'status_filter': status_filter,
        'low_stock_count': Product.objects.filter(stock__lte=5, stock__gt=0).count(),
        'out_stock_count': Product.objects.filter(stock=0).count(),
        'total_variants': Product.objects.count(),
    }
    return render(request, 'admin/stock_management.html', context)

# Create your views here.
