from django.urls import path
from .import views


urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('verify_otp/',views.verify_otp_view,name='verify_otp'),
    path('resend_otp/', views.resend_otp, name='resend_otp'),
    path('login/', views.user_login, name='login'),
    path('forgot_password/', views.forgot_password_request, name='forgot_password'),
    path('verify_reset_otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('admin_login/',views.admin_login,name='admin_login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/user_management/', views.admin_user_management, name='user_management'),
    path('toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    

]