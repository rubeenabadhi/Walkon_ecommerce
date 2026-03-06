"""
URL configuration for walkon_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include
from django.shortcuts import render
from django.conf.urls import handler404
from django.conf.urls.static import static




urlpatterns = [
    path("grappelli/", include("grappelli.urls")), # grappelli means admin panel it use for django
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('accounts/', include('allauth.urls')),
    path('dashboard/', include('admin_dashboard.urls')),
    path('', include('product.urls')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('address/', include("address.urls")),
    path('wishlist/',include("wishlist.urls")),
    path('checkout/', include('checkout.urls')),
    path('order/',include("order.urls")),
    path('offers/', include('offers.urls')),
    path('wallet/', include('wallet.urls')),
    path('review/', include('review.urls')),
    path('pages/', include('pages.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
def custom_404_view(request, exception):
    return render(request, "404.html", status=404)
def custom_500_view(request):
    return render(request, "500.html", status=500)
def custom_403_view(request, exception):
    return render(request, "403.html", status=403)

handler404 = custom_404_view
handler500 = custom_500_view
handler403 = custom_403_view



