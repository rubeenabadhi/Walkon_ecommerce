from . import views
from django.urls import path

urlpatterns = [
    #====================================USER VIEW====================================
    #_
    path('', views.orders, name='orders'),
    path('cancel/<uuid:order_id>/', views.cancel_order, name='cancel_order'),
    path('cancel-item/<uuid:item_id>/', views.cancel_item, name='cancel_item'),
    path('order_details/<str:order_number>/', views.order_detail, name='order_details'),
    path('return/<uuid:item_id>/', views.return_item, name='return_item'),
    path('return-order/<uuid:order_id>/', views.return_order, name='return_order'),
    path("invoice/<uuid:order_id>/", views.order_invoice_pdf, name="invoice_pdf"),

    #====================================ADMIN VIEW====================================
    path("admin/orders/", views.admin_orders, name="admin_orders"),
    path("admin/orders/<str:order_number>/", views.admin_order_detail, name="admin_order_detail"),
    path("admin/orders/<str:order_number>/update-status/", views.admin_order_status, name="update_order_status"),

]