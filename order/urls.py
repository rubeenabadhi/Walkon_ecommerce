from . import views
from django.urls import path

urlpatterns = [
    #====================================USER VIEW====================================
    #_
    path('', views.orders, name='orders'),
    path('cancel/<uuid:order_id>/', views.cancel_order, name='cancel_order'),
    path('cancel-item/<uuid:item_id>/', views.cancel_item, name='cancel_item'),
    path('order-details/<str:order_number>/', views.order_detail, name='order_details'),
    path("invoice/<uuid:order_id>/", views.order_invoice_pdf, name="invoice_pdf"),
    path("request-return-item/<uuid:item_id>/", views.request_return_item, name="request_return_item"),
    path("request-return/<uuid:order_id>/", views.request_return_order, name="request_return"),

    #====================================ADMIN VIEW====================================
    path("admin/orders-view/", views.admin_orders, name="admin_orders"),
    path("admin/order-details/<str:order_number>/", views.admin_order_detail, name="admin_order_details"),
    path("admin/order-action/<str:order_number>/update-status/", views.admin_order_action, name="update_order_status"),
    path("admin/return-requests/", views.admin_return_requests_list, name="admin_return_requests"),
    path("admin/<str:order_number>/action/", views.admin_order_action, name="admin_order_action"),
    path("admin/returns-process/<uuid:request_id>/process/", views.admin_process_return, name="admin_process_return"),
    path("admin/return-request-details/<uuid:request_id>/", views.admin_return_request_details, name="admin_return_details"),

]