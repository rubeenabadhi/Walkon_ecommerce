from .import views
from django.urls import path

app_name = "cart"  #  THIS is the namespace

urlpatterns = [
    path('add/<slug:slug>/', views.add_to_cart, name='add_to_cart'),
    path('update_cart/<int:cart_item_id>/', views.update_cart, name='update_cart'),
    path('remove_from_cart/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('', views.cart, name='cart'),
]