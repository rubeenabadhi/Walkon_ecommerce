from django.db import models
from django.conf import settings
from django.utils import timezone
from product.models import Product 
import uuid
# Create your models here
# models.py
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=10,
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')]
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(default=1)  # per user
    
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True )

    def __str__(self):
        return self.code
    
    
    #discount_type if percentage convert to fixed
    def get_discounted_price(self, price):
        if self.discount_type == 'percentage':
            return price * (1 - self.discount_value / 100)
        else:
            return price - self.discount_value
    
    
    
# Coupon usage by User
class UserCoupon(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, editable=False, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'coupon')

    def __str__(self):
        return f"{self.user.username} - {self.coupon.code} (Used: {self.used_count})"
    
# Product Offer
class ProductOffer(models.Model):
    product = models.ForeignKey("product.Product", on_delete=models.CASCADE, related_name="product_offers")
    discount_percentage = models.PositiveIntegerField()
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}% OFF"
    
    def is_active(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to
    


# Category Offer
class CategoryOffer(models.Model):
    category = models.ForeignKey("product.Category", on_delete=models.CASCADE, related_name="category_offers")
    discount_percentage = models.PositiveIntegerField()
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category.name} - {self.discount_percentage}% OFF"
    class Meta:
        verbose_name = "Category Offer"
        verbose_name_plural = "Category Offers"
    def is_active(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to
    

#================================================REFERREL OFFER===============================================

class Referral(models.Model):
    referrer=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals')
    referred_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='referred_by', blank=True)
    referral_code=models.CharField(max_length=10, unique=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        
        return f"{self.referrer.username} - {self.referral_code}" #means referrer is user and referred_by is referrel code 