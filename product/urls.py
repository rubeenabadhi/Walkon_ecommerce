from django.urls import path
from .import views

urlpatterns = [
    #========================  Admin Views  ========================
    path('add-gender/',views.add_gender,name='add_gender'),
    path('add-brand/', views.add_brand, name='add_brand'),
    path('add-category/', views.add_category, name='add_category'),
    path('add-size/', views.add_size, name='add_size'),
    path('add-color/', views.add_color, name='add_color'),
    path('add-product/', views.add_product, name='add_product'),
    path('products/', views.product_list, name='products'),
    path('products/<slug:slug>/view/', views.product_view, name='admin_product_details'),
    path('products/<slug:slug>/edit/', views.edit_product, name='edit_product'),
    path('products/<slug:slug>/delete/', views.delete_product, name='delete_product'),
    path('master/', views.admin_master_view, name='admin_master'),
    path("delete-variant/", views.ajax_delete_variant, name="ajax_delete_variant"),
    path("edit-master-item/", views.ajax_edit_variant, name="ajax_edit_variant"),
    path('stock-management/', views.stock_management, name='stock_management'),

    #========================  User Views  ========================

    path('all-products/', views.user_product_list, name='all_products'),
    path('product/<slug:slug>/', views.product_detail, name='product_details'),
    path('products/<str:gender_label>/', views.products_by_gender, name='products_by_gender'),
    path('new-arrivals/', views.new_arrivals, name='new_arrivals'),
    path('product/<int:product_id>/sizes/', views.product_sizes, name='product_sizes'),


]
