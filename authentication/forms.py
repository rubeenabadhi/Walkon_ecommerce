from django import forms
from .models import CustomUser


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'mobile_number', 'profile_picture']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control rounded-3 shadow-sm',
                'placeholder': 'Enter your username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control rounded-3 shadow-sm',
                'readonly': 'readonly'  # Prevent direct editing
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control rounded-3 shadow-sm',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control rounded-3 shadow-sm',
                'placeholder': 'Enter your last name'
            }),
            'mobile_number': forms.TextInput(attrs={
                'class': 'form-control rounded-3 shadow-sm',
                'placeholder': 'Enter your phone number'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control form-control-lg border-0 bg-light shadow-sm rounded-3'
            }),
        }
