from django.urls import path
from .import views

urlpatterns = [
    #========================  Admin Views  ========================
    path('add_gender/',views.add_gender,name='add_gender'),
    path('add_brand/', views.add_brand, name='add_brand'),
    path('add_category/', views.add_category, name='add_category'),
    path('add_size/', views.add_size, name='add_size'),
    path('add_color/', views.add_color, name='add_color'),
    path('add_product/', views.add_product, name='add_product'),
    path('products/', views.product_list, name='products'),
    path('products/<slug:slug>/view/', views.product_view, name='admin_product_details'),
    path('products/<slug:slug>/edit/', views.edit_product, name='edit_product'),
    path('products/<slug:slug>/delete/', views.delete_product, name='delete_product'),

    #========================  User Views  ========================

    path('all_products/', views.user_product_list, name='all_products'),
    path('product/<slug:slug>/', views.product_detail, name='product_details'),
    path('products/kids/', views.kids_products, name='kids_products'),
    path('products/men/', views.men_products, name='men_products'),
    path('products/new_arrivals/', views.new_arrivals, name='new_arrivals'),

]
