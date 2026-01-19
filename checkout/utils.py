from decimal import Decimal



def calculate_final_amount(cart_items, coupon=None):
    subtotal = sum(Decimal(ci.variant.price) * ci.quantity for ci in cart_items)
    print("Calculating final amount. Subtotal:", subtotal)
    discount = Decimal('0.00')

    if coupon:
        if coupon.discount_type == 'amount':
            discount = min(Decimal(coupon.discount_value), subtotal)
            print("Amount-based coupon discount applied:", discount)
        elif coupon.discount_type == 'percentage':
            discount = subtotal * (Decimal(coupon.discount_value) / 100)
            print("Percentage-based coupon discount applied:", discount)

    final_total = subtotal - discount
    print("Subtotal:", subtotal, "Discount:", discount, "Final Total:", final_total)
    return subtotal.quantize(Decimal('0.01')), discount.quantize(Decimal('0.01')), final_total.quantize(Decimal('0.01'))
