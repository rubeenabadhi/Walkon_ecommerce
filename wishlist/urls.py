from .import views
from django.urls import path

urlpatterns = [
    path('', views.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", views.toggle_wishlist, name="toggle_wishlist"),
    path('add/<int:variant_id>/', views.add_to_wishlist, name="add_to_wishlist"),
    path('remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path("add-to-cart/<int:variant_id>/", views.move_to_cart, name="move_to_cart"),

] 