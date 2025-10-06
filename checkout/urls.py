from . import views
from django.urls import path

urlpatterns = [
    path('select_address/', views.select_address, name='select_address'),
    path('add_address/', views.add_address_checkout, name='add_address_checkout'),
    path('edit_address/<int:address_id>/', views.edit_address_checkout, name='edit_address_checkout'),
    path('payment/', views.select_payment, name='select_payment'),
    path("create-razorpay-order/<uuid:order_id>/", views.create_razorpay_order, name="create_razorpay_order"),
    path('verify_razorpay_payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('place_order/', views.place_order, name='place_order'),    
    path('order-success/<str:order_id>/', views.order_success, name='order_success'),
    path('payment-failure-save/<str:order_id>/', views.save_payment_failure, name='payment_failure_save'),
    path('payment-failed/', views.payment_failure, name='payment_failure'),
]
