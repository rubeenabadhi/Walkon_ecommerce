from django.db import models
from django.utils.text import slugify
from django.conf import settings

# Create your models here.
#Gender model
class Gender(models.Model):
    label = models.CharField(max_length=50)
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
    slug = models.SlugField(max_length=150, unique=True)
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

class ProductType(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Type"
        verbose_name_plural = "Product Types"

    def __str__(self):
        return self.name

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
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='colors')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Color"
        verbose_name_plural = "Colors"

    def __str__(self):
        return f"{self.name} ({self.hex_code})"


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.URLField(max_length=500, blank=True)  # Main product image    is_available = models.BooleanField(default=True)
    slug = models.SlugField(max_length=250, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name='products')
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='added_products')
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, related_name='products')
    product_type = models.ForeignKey(ProductType, on_delete=models.SET_NULL, null=True, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Image(models.Model):
    url = models.URLField(max_length=500) # URL of the image from Cloudinary
    alt_text = models.CharField(max_length=255, blank=True)  # Optional alt text for the image
    uploaded_at = models.DateTimeField(auto_now_add=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='images')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Image"
        verbose_name_plural = "Images"

    def __str__(self):
        return f"Image for {self.product.name}"

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, related_name='variants')
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"

    def __str__(self):
        return f"{self.product.name} - {self.size.label if self.size else ''} {self.color.name if self.color else ''}"