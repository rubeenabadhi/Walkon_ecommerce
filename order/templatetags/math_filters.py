from django import template
from django.db.models import F, Sum


register = template.Library()

@register.filter
def mul(value, arg):
    return float(value) * float(arg)

@register.filter
def total_amount(items):
    return items.aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0
'''this file is used to create custom template filters for mathematical operations in Django templates. 
It defines two filters: 'mul' for multiplication and 'total_amount' for calculating the total amount from a queryset of items.'''