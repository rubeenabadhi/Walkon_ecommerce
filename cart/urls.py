from .import views
from django.urls import path

app_name = "cart"  #  THIS is the namespace

urlpatterns = [
    path('', views.cart, name='cart'),
    path('add/<slug:slug>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:cart_item_id>/', views.update_cart, name='update_cart'),
    
]