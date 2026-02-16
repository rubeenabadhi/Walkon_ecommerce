from django.urls import path
from .import views


urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('verify-otp/',views.verify_otp_view,name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('login/', views.user_login, name='login'),
    path('forgot-password/', views.forgot_password_request, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('admin-login/',views.admin_login,name='admin_login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/user_management/', views.admin_user_management, name='user_management'),
    path('toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('profile/<int:user_id>/', views.user_profile, name='user_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path("change-email/", views.request_email_change, name="change_email"),
    path("verify-email-otp/", views.verify_email_otp, name="verify_email_change_otp"),
    path("resend-email-otp/", views.resend_email_change_otp, name="resend_email_change_otp"),

    
]