from django.db import models
from django.forms import ValidationError
from authentication.models import CustomUser


# Create your models here.
class Address(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100,default=None,null=True,blank=True)
    phone_number = models.CharField(max_length=15,default=None,null=False,blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    street = models.CharField(max_length=200, default="", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.address

    class Meta:
        ordering = ['created_at']  
    def clean(self):
        if self.full_name and len(self.full_name) < 3:
            raise ValidationError("Full name must be at least 3 characters long.")
        if self.full_name and len(self.full_name) > 30:
            raise ValidationError("Full name must be at most 30 characters long.")
        if self.phone_number and not self.phone_number.isdigit():
            raise ValidationError("Phone number must contain only numbers.")
        if self.phone_number and not self.phone_number.isdigit():
            raise ValidationError("Phone number must contain only numbers.")
        if self.phone_number and len(self.phone_number) < 10 or len(self.phone_number) > 15:
            raise ValidationError("Phone number must be at least 10 digits long and at most 15 digits long.")
        if self.pincode and not self.pincode.isdigit():
            raise ValidationError("Pincode must contain only numbers.")
        if self.pincode and len(self.pincode) < 6:
            raise ValidationError("Pincode must be at least 6 digits long.")
        if self.pincode and len(self.pincode) > 10:
            raise ValidationError("Pincode must be at most 10 digits long.")
        if self.city and len(self.city) < 3:
            raise ValidationError("City must be at least 3 characters long.")
        if self.city and len(self.city) > 20:
            raise ValidationError("City must be at most 20 characters long.")
        if self.state and len(self.state) < 3:
            raise ValidationError("State must be at least 3 characters long.")
        if self.state and len(self.state) > 20:
            raise ValidationError("State must be at most 20 characters long.")
        if self.country.lower() != 'india':
            raise ValidationError("Country must be India.")
        
#================