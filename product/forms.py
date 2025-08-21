from django import forms
from .models import *
from cloudinary.forms import CloudinaryFileField
from django.utils.text import slugify

class GenderForm(forms.ModelForm):
    class Meta:
        model = Gender
        fields = ['label', 'description']
        widgets = {
            'label': forms.TextInput(attrs={ 
                'class': 'form-control rounded-3',
                'placeholder': 'Enter gender name (e.g., Male, Female)',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control rounded-3',
                'rows': 4,
                'placeholder': 'Enter description'
            }),
        }
        labels = {
            'label': 'Gender Name',
            'description': 'Description',
        }

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'slug']
        widgets = { 
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter brand name',
                'required': 'required'
            }),
            'slug': forms.TextInput(attrs={ 
                'class': 'form-control rounded-3',
                'placeholder': 'Enter slug (optional)',
            }),
        }
        labels = {
            'name': 'Brand Name',
            'slug': 'Slug (optional)',
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter category name',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control rounded-3',
                'rows': 4,
                'placeholder': 'Enter description'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter slug (optional)',
            }),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description',
            'slug': 'Slug (optional)',
        }
class SizeForm(forms.ModelForm):
    class Meta:
        model = Size
        fields = ['label']
        widgets = {
            'label': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter size label (e.g., S, M, L)',
                'required': 'required'
            }),
        }
        labels = {
            'label': 'Size Label',
        }
class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['name', 'hex_code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter color name',
                'required': 'required'
            }),
            'hex_code': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter hex code (e.g., #FFFFFF)',
                'required': 'required'
            }),
        }
        labels = {
            'name': 'Color Name',
            'hex_code': 'Hex Code',
        }


#product forms
class ProductForm(forms.ModelForm):
    primary_image = CloudinaryFileField(
        options={'folder': 'products'},
        required=False
    )

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'primary_image',
            'is_available', 'category', 'brand', 'gender'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product description'}),
            'primary_image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'name': 'Product Name',
            'description': 'Description',
            'primary_image': 'Primary Image',
            'is_available': 'Available for Sale',
            'category': 'Category',
            'brand': 'Brand',
            'gender': 'Gender',
        }


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['url', 'alt_text']
        widgets = {
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Image URL'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Alt text for the image'}),
        }
        labels = {
            'url': 'Image URL',
            'alt_text': 'Alt Text',
        }

class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['size', 'price', 'stock' , 'color']
        widgets = {
            'size': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter variant price'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter variant stock quantity'}),
            'color': forms.Select(attrs={'class': 'form-select'}),

        }
        labels = {
            'size': 'Size',
            'price': 'Price ',
            'stock': 'Stock Quantity',
            'color': 'Color',
        }