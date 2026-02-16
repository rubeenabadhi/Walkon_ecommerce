from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
import random
from django.forms import ValidationError
from django.utils import timezone
from django.conf import settings
# Custom user model extending AbstractUser


class CustomUser(AbstractUser):
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)  # unique=False by default
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    referrel_code = models.CharField(max_length=10, unique=True, null=True, blank=True, default=None)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  #it is not required for CustomUser,it is for superuser creation

    def __str__(self):
        return self.username
    def clean(self):
        if self.mobile_number and not self.mobile_number.isdigit():
            raise ValidationError("Mobile number must contain only digits.")
        if self.mobile_number and len(self.mobile_number) < 10:
            raise ValidationError("Mobile number must be at least 10 digits long.")
        if self.mobile_number and len(self.mobile_number) > 15:
            raise ValidationError("Mobile number must be at most 15 digits long.")
        if self.username and self.username.isalnum() == False:
            raise ValidationError("Username must be alphanumeric.")
        if self.username and len(self.username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
    
    