from django.urls import path
from .import views

urlpatterns = [
    path('add/', views.add_address, name='add_address'),
    path('all_address/', views.address, name='address'),
    path('edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('delete/<int:address_id>/', views.delete_address, name='delete_address'),
    
]