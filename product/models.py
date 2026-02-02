from django.db import models
from django.utils.text import slugify
from django.conf import settings
from cloudinary.models import CloudinaryField
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from django.db.models import Avg


# Create your models here.
#Gender model
class Gender(models.Model):
    label = models.CharField(max_length=50)
    description = models.TextField(blank=True)  # Optional description field
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gender"
        verbose_name_plural = "Genders"

    def __str__(self):
        return self.label

class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):# Ensure slug is generated from name
        if not self.slug:# if slug is not generated
            self.slug = slugify(self.name)# generate slug
        super().save(*args, **kwargs)# save the instance to the database 

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=150, unique=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Size(models.Model):
    label = models.CharField(max_length=50)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Size"
        verbose_name_plural = "Sizes"

    def __str__(self):
        return self.label

class Color(models.Model):
    name = models.CharField(max_length=50)
    hex_code = models.CharField(max_length=7)  # e.g., #FFFFFF
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Color"
        verbose_name_plural = "Colors"

    def __str__(self):
        return f"{self.name} ({self.hex_code})"


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    primary_image = CloudinaryField(blank=True, null=True)  # Primary image for the product
    is_available = models.BooleanField(default=True)  # To indicate if the product is available for purchase
    is_active = models.BooleanField(default=True)  # To indicate if the product is active
    slug = models.SlugField(max_length=250, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name='products')
    stock = models.PositiveIntegerField(default=0)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='added_products')
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    #offers
    

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def average_rating(self):
        avg = self.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg or 0, 1)  
    #count reviews
    @property
    def review_count(self):
        return self.reviews.count()  
    
    def get_display_price(self):
        return self.variants.order_by('price').first()
    

        # ================== OFFER PRICE METHOD ==================
 
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, related_name='variants')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        unique_together = ('product', 'size', 'color') # Ensure unique combination of product, size, and color

    def __str__(self):
        return f"{self.product.name} - {self.size.label if self.size else ''} {self.color.name if self.color else ''}"
    
    def get_offer_price(self):
        from offers.models import ProductOffer, CategoryOffer  # import inside method
        now = timezone.now()

    # Convert base price to Decimal
        base_price = Decimal(self.price)

    # Product-level offer
        product_offer = ProductOffer.objects.filter(
            product=self.product,  # ✅ should be self.product, not self
            active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ).first()

        if product_offer:
            discount = Decimal(product_offer.discount_percentage) / Decimal(100)
            discount_price = base_price * (Decimal(1) - discount)
            return discount_price.quantize(Decimal('0.01'))

    # Category-level offer
        if self.product and self.product.category:
            category_offer = CategoryOffer.objects.filter(
                category=self.product.category,
                active=True,
                valid_from__lte=now,
                valid_to__gte=now
            ).first()

            if category_offer:
                discount = Decimal(category_offer.discount_percentage) / Decimal(100)
                discount_price = base_price * (Decimal(1) - discount)
                return discount_price.quantize(Decimal('0.01'))

        return base_price
    
    def get_offer_percentage(self):
        from offers.models import ProductOffer, CategoryOffer  # import inside method
        now = timezone.now()

        # Product-level offer
        product_offer = ProductOffer.objects.filter(
            product=self.product,
            active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ).first()

        if product_offer:
            return product_offer.discount_percentage

        # Category-level offer
        if self.product and self.product.category:
            category_offer = CategoryOffer.objects.filter(
                category=self.product.category,
                active=True,
                valid_from__lte=now,
                valid_to__gte=now
            ).first()

            if category_offer:
                return category_offer.discount_percentage

        return 0  # No offer

    
class Image(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images',default=None,null=True,blank=True)  # One-to-many relationship with variant-based images
    image = CloudinaryField(blank=True, null=True) 
    alt_text = models.CharField(max_length=255, blank=True)  # Optional alt text for the image
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Image"
        verbose_name_plural = "Images"

    def __str__(self):
        if self.variant:
            return f"Image for {self.variant.product.name} - {self.alt_text or 'No Alt Text'}"
        return f"Image (Unassigned) - {self.alt_text or 'No Alt Text'}"