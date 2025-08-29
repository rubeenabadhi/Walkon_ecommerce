from django.urls import path
from .import views

urlpatterns = [
    path('add_gender/',views.add_gender,name='add_gender'),
    path('add_brand/', views.add_brand, name='add_brand'),
    path('add_category/', views.add_category, name='add_category'),
    path('add_size/', views.add_size, name='add_size'),
    path('add_color/', views.add_color, name='add_color'),
    path('add_product/', views.add_product, name='add_product'),
    path('products/', views.product_list, name='products'),
    path('products/<slug:slug>/view/', views.product_view, name='admin_product_details'),
    path('product/<slug:slug>/edit/', views.edit_product, name='edit_product'),
    path('product/<slug:slug>/delete/', views.delete_product, name='delete_product'),
    path('all_products/', views.user_product_list, name='all_products'),
    path('product/<slug:slug>/', views.product_details, name='product_details'),
    path('products/kids/', views.kids_products, name='kids_products'),
    # Add more paths for other product management views as needed
]
