# product/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def discount_percentage(original_price, offer_price):
    try:
        if original_price and offer_price:
            discount = (original_price - offer_price) / original_price * 100
            return round(discount, 0)
    except:
        return 0
    return 0
