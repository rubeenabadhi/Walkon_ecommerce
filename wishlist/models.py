from django.db import models
from django.conf import settings
from product.models import ProductVariant

# Create your models here.
class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlists")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wishlist of {self.user}"

    class Meta:
        ordering = ["-created_at"]


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("wishlist", "product_variant")  # avoid duplicates

    def __str__(self):
        return f"{self.product_variant} in {self.wishlist}"

    class Meta:
        ordering = ["-added_at"]