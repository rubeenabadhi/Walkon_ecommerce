from .import views
from django.urls import path

urlpatterns = [
    #-------------------------------------------------------ADMIN VIEW-------------------------------------------------------
    path('coupons/', views.admin_coupons, name='admin_coupons'),
    path('coupons/load-form/', views.load_coupon_form, name='load_coupon_form'),
    path('coupons/load-form/<int:pk>/', views.load_coupon_form, name='load_coupon_form'),
    path('coupons/save/', views.save_coupon, name='save_coupon'),
    path('coupons/save/<int:pk>/', views.save_coupon, name='save_coupon'),
    path('coupons/delete/<int:pk>/', views.delete_coupon, name='delete_coupon'),

    #-------------------------------------------------------USER VIEW-------------------------------------------------------
    path('my-coupons/', views.available_coupons, name='user_coupons'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('refer-earn/', views.refer_earn, name='refer_earn'),
    path('my-referrals/', views.my_referrals, name='my_referrals'),
]
