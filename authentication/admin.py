from django.contrib import admin
from .models import CustomUser

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active')
    ordering = ('email',)

    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_active')
        }),
    )

    add_fieldsets = (
        (None, {
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'is_staff', 'is_active')}
         ),
    )