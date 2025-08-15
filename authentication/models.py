from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
import random
from django.utils import timezone
from django.conf import settings
# Custom user model extending AbstractUser


class CustomUser(AbstractUser):
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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  #it is not required for CustomUser,it is for superuser creation
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.username
    
    