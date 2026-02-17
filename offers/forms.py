from django.forms import ModelForm
from .models import *
from django import forms

class CouponForm(ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'active', 'usage_limit', 'min_order_amount']
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'code': 'Coupon Code',
            'discount_type': 'Discount Type',
            'discount_value': 'Discount Value',
            'valid_from': 'Valid From',
            'valid_to': 'Valid To',
            'active': 'Is Active',
            'usage_limit': 'Usage Limit per User',
            'min_order_amount': 'Minimum Order Amount',
        }

    def clean_discount_value(self):
        value = self.cleaned_data.get('discount_value')
        discount_type = self.cleaned_data.get('discount_type')
        
        if value is None:
            raise forms.ValidationError("This field is required.")
        if value <= 0:
            raise forms.ValidationError("Discount value must be greater than 0")
        if discount_type == 'percentage':
            if value > 100:
                raise forms.ValidationError("Percentage discount cannot be greater than 100.")
            if value <= 0:
                raise forms.ValidationError("Percentage discount must be greater than 0.")
            
        if discount_type == 'fixed':
            if value <= 0:
                min_amount = self.cleaned_data.get('min_order_amount', 0)
                raise forms.ValidationError("Fixed discount must be greater than 0.")
            if value > min_amount:
                raise forms.ValidationError("Fixed discount cannot be greater than minimum order amount.")
        return value
    def clean_usage_limit(self):
        usage_limit = self.cleaned_data.get('usage_limit')
        if usage_limit is None:
            raise forms.ValidationError("This field is required.")
        if usage_limit <= 0:
            raise forms.ValidationError("Usage limit must be greater than 0.")
        if usage_limit > 2:
            raise forms.ValidationError("Usage limit cannot be greater than 2.")
        return usage_limit
    

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        if valid_from and valid_to and valid_from >= valid_to:
            raise forms.ValidationError("Valid from must be earlier than valid to")
        return cleaned_data
    


class ProductOfferForm(ModelForm):
    class Meta:
        model = ProductOffer
        fields = ['product', 'discount_percentage', 'valid_from', 'valid_to', 'active']
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'product': 'Product',
            'discount_percentage': 'Discount Percentage',
            'valid_from': 'Valid From',
            'valid_to': 'Valid To',
            'active': 'Is Active',
        }
        help_texts = {
            'discount_percentage': 'Enter the discount percentage (e.g., 10 for 10%).',
        }

    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount <= 0 or discount > 100:
            raise forms.ValidationError("Discount percentage must be between 1 and 100.")
        return discount 

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')

        if valid_from and valid_to and valid_from >= valid_to:
            raise forms.ValidationError("The 'valid from' date must be earlier than the 'valid to' date.")
        return cleaned_data


class CategoryOfferForm(ModelForm):
    class Meta:
        model = CategoryOffer
        fields = ['category', 'discount_percentage', 'valid_from', 'valid_to', 'active']
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'category': 'Category',
            'discount_percentage': 'Discount Percentage',
            'valid_from': 'Valid From',
            'valid_to': 'Valid To',
            'active': 'Is Active',
        }
        help_texts = {
            'discount_percentage': 'Enter the discount percentage (e.g., 10 for 10%).',
        }

    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount <= 0 or discount > 100:
            raise forms.ValidationError("Discount percentage must be between 1 and 100.")
        return discount 

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')

        if valid_from and valid_to and valid_from >= valid_to:
            raise forms.ValidationError("The 'valid from' date must be earlier than the 'valid to' date.")
        return cleaned_data

    class Meta:
        model = CategoryOffer
        fields = ['category', 'discount_percentage', 'valid_from', 'valid_to', 'active']
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'category': 'Category',
            'discount_percentage': 'Discount Percentage',
            'valid_from': 'Valid From',
            'valid_to': 'Valid To',
            'active': 'Is Active',
        }
        help_texts = {
            'discount_percentage': 'Enter the discount percentage (e.g., 10 for 10%).',
        }
        error_messages = {
            'category': {
                'unique': "An offer for this category already exists.",
            },
        }   
    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount <= 0 or discount > 100:
            raise forms.ValidationError("Discount percentage must be between 1 and 100.")
        return discount 
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')

        if valid_from and valid_to and valid_from >= valid_to:
            raise forms.ValidationError("The 'valid from' date must be earlier than the 'valid to' date.")
        return cleaned_data
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Any additional processing can be done here
        if commit:
            instance.save()
        return instance