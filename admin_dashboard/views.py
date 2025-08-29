from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
# Create your views here
# admin dashboard
@never_cache
@staff_member_required
def admin_dashboard(request):
    return render(request, 'admin/dashboard.html')