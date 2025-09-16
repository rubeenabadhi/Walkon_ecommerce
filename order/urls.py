from . import views
from django.urls import path

urlpatterns = [
    path('', views.orders, name='orders'),
    path('cancel/<str:order_number>/', views.cancel_order, name='cancel_order'),
    path('cancel-item/<uuid:item_id>/', views.cancel_item, name='cancel_item'),
    path('order_details/<str:order_number>/', views.order_detail, name='order_details'),
    path("invoice/<uuid:order_id>/", views.order_invoice_pdf, name="invoice_pdf"),

]