from django import forms
from .models import *
from cloudinary.forms import CloudinaryFileField
from django.utils.text import slugify
from django.forms.models import inlineformset_factory

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


# Main Product Formclass ProductForm(forms.ModelForm):
# Product Form

# Variant Form
class ProductFilterForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories"
    )

    brand = forms.ModelChoiceField(
        queryset=Brand.objects.all(),
        required=False,
        empty_label="All Brands"
    )

    gender = forms.ModelChoiceField(
        queryset=Gender.objects.all(),
        required=False,
        empty_label="All"
    )

    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Min Price"
    )

    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Max Price"
    )

    sort_by = forms.ChoiceField(
        choices=[
            ("", "Sort By"),
            ("price_low", "Price: Low to High"),
            ("price_high", "Price: High to Low"),
            ("latest", "Latest"),
            ("oldest", "Oldest"),
        ],
        required=False
    )
