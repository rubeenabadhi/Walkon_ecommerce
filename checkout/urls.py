from . import views
from django.urls import path

urlpatterns = [
    path('select_address/', views.select_address, name='select_address'),
    path('add_address/', views.add_address_checkout, name='add_address_checkout'),
    path('edit_address/<int:address_id>/', views.edit_address_checkout, name='edit_address_checkout'),
    path('payment/', views.select_payment, name='select_payment'),
    path("create-razorpay-order/<uuid:order_id>/", views.create_razorpay_order, name="create_razorpay_order"),
    path('verify-razorpay-payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('place_order/', views.place_order, name='place_order'),    
    path('checkout_summary/', views.checkout_summary, name='checkout_summary'),

]
