from .import views
from django.urls import path

urlpatterns = [
    #========================  User Views  ========================
    path('', views.wallet, name="wallet"),
    path('add-money/', views.add_money, name="add_money"),
    path('wallet-payment-success/', views.wallet_payment_success, name="wallet_payment_success"),

    #========================  Admin Views  ========================
    path('wallets/', views.admin_wallets, name='admin_wallets'),
    path('wallet/<int:wallet_id>/', views.admin_wallet_detail, name='admin_wallet_details'),
]