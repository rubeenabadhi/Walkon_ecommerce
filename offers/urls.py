from .import views
from django.urls import path

urlpatterns = [
    #-------------------------------------------------------ADMIN VIEW-------------------------------------------------------
    path('coupons/', views.admin_coupons, name='admin_coupons'),
    path('coupons-users/<int:coupon_id>/', views.users_used_coupons, name='coupon_users'),
    path('coupons/load-form/', views.load_coupon_form, name='load_coupon_form'),
    path('coupons/load-form/<int:pk>/', views.load_coupon_form, name='load_coupon_form'),
    path('coupons/save/', views.save_coupon, name='save_coupon'),
    path('coupons/save/<int:pk>/', views.save_coupon, name='save_coupon'),
    path('coupons/delete/<int:pk>/', views.delete_coupon, name='delete_coupon'),
    path('referrals/', views.admin_referrals, name='admin_referrals'),
    path('product-offers/', views.admin_product_offers, name='admin_product_offers'),
    path('product-offers/load-form/', views.load_product_offer_form, name='load_product_offer_form'),
    path('product-offers/load-form/<int:pk>/', views.load_product_offer_form, name='load_product_offer_form'),
    path('product-offers/save/', views.save_product_offer, name='save_product_offer'),
    path('product-offers/save/<int:pk>/', views.save_product_offer, name='save_product_offer'),
    path('product-offers/delete/<int:pk>/', views.delete_product_offer, name='delete_product_offer'),
    path('category-offers/', views.admin_category_offers, name='admin_category_offers'),
    path('category-offers/load-form/', views.load_category_offer_form, name='load_category_offer_form'),
    path('category-offers/load-form/<int:pk>/', views.load_category_offer_form, name='load_category_offer_form'),
    path('category-offers/save/', views.save_category_offer, name='save_category_offer'),
    path('category-offers/save/<int:pk>/', views.save_category_offer, name='save_category_offer'),
    path('category-offers/delete/<int:pk>/', views.delete_category_offer, name='delete_category_offer'),

    #-------------------------------------------------------USER VIEW-------------------------------------------------------
    path('my-coupons/', views.available_coupons, name='user_coupons'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('refer-earn/', views.refer_earn, name='refer_earn'),
    path('my-referrals/', views.my_referrals, name='my_referrals'),

]
