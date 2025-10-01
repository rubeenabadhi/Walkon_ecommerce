from django.db import models
from django.conf import settings
from django.utils import timezone
from product.models import Product 
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
    
# Coupon usage by User
class UserCoupon(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_count = models.IntegerField(default=0)

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

    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}% OFF"


# Category Offer
class CategoryOffer(models.Model):
    category = models.ForeignKey("product.Category", on_delete=models.CASCADE, related_name="category_offers")
    discount_percentage = models.PositiveIntegerField()
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.category.name} - {self.discount_percentage}% OFF"
    class Meta:
        verbose_name = "Category Offer"
        verbose_name_plural = "Category Offers"
