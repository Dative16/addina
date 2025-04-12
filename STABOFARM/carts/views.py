from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation, ProductVariation
from .models import Cart, CartItem, BulkDiscount, CustomerDiscount, ExpiryDiscount, Coupon, Promotion, ClearanceDiscount, DiscountRule, DiscountApproval
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages

from datetime import date
from django.utils import timezone




# FIXME  ================ DISCOUNT SECTION ===============


def calculate_bulk_discount(cart_item):
    bulk_discount = BulkDiscount.objects.filter(product=cart_item.product, min_quantity__lte=cart_item.quantity).first()
    if bulk_discount:
        discount_amount = (cart_item.product_variation.sub_total * bulk_discount.discount_percentage) / 100
        cart_item.discount_amount += discount_amount
        cart_item.save()
        return discount_amount * cart_item.quantity
    return 0

def calculate_expiry_discount(cart_item):
    today = date.today()
    expiry_discount = None
    if cart_item.product.expire_date:
        days_left = (cart_item.product.expire_date - today).days
        expiry_discount = ExpiryDiscount.objects.filter(product=cart_item.product, days_before_expiry__gte=days_left).first()

    if expiry_discount:
        discount_amount = (cart_item.product_variation.sub_total * expiry_discount.discount_percentage) / 100
        cart_item.discount_amount += discount_amount
        cart_item.save()
        return discount_amount * cart_item.quantity
    return 0

def apply_coupon(cart_item, coupon_code):
    try:
        coupon = Coupon.objects.get(code=coupon_code, active=True, valid_from__lte=date.today(), valid_to__gte=date.today())
        total_discount = (cart_item.sub_total() * coupon.discount_percentage) / 100
        cart_item.discount_amount += total_discount
        cart_item.save()
        return total_discount
    except Coupon.DoesNotExist:
        return 0


def calculate_promotion_discount(cart_item):
    now = timezone.now()
    promotion = Promotion.objects.filter(product=cart_item.product, start_date__lte=now, end_date__gte=now).first()

    if promotion:
        discount_amount = (cart_item.product_variation.sub_total * promotion.discount_percentage) / 100
        cart_item.discount_amount += discount_amount
        cart_item.save()
        return discount_amount * cart_item.quantity
    return 0

def calculate_clearance_discount(cart_item):
    clearance_discount = ClearanceDiscount.objects.filter(product=cart_item.product, min_stock__lte=cart_item.product.stock).first()

    if clearance_discount:
        discount_amount = (cart_item.product_variation.sub_total * clearance_discount.discount_percentage) / 100
        cart_item.discount_amount += discount_amount
        cart_item.save()
        return discount_amount * cart_item.quantity
    return 0

def calculate_total_discount(cart_item, coupon_code=None):
    bulk_discount = calculate_bulk_discount(cart_item)
    expiry_discount = calculate_expiry_discount(cart_item)
    promotion_discount = calculate_promotion_discount(cart_item)
    clearance_discount = calculate_clearance_discount(cart_item)

    total_discount = bulk_discount + expiry_discount + promotion_discount + clearance_discount

    if coupon_code:
        total_discount += apply_coupon(cart_item, coupon_code)
    cart_item.discount_amount = total_discount
    cart_item.save()
    return total_discount


def apply_customer_discount(user, item):
    customer_discount = CustomerDiscount.objects.filter(customer=user, is_active=True).first()
    if customer_discount:
        item.discount_amount = item.product_variation.sub_total * (1 - (customer_discount.discount_percentage / 100))
        item.save()

def apply_discounts(cart_items):
    for item in cart_items:
        discounts = DiscountRule.objects.filter(is_active=True)
        for discount in discounts:
            if discount.is_applicable(item.product, item.quantity):
                item.discount_amount = item.product_variation.sub_total * (1 - (discount.discount_percentage / 100))
                item.save()


def approve_discount(approval_id, manager):
    approval = DiscountApproval.objects.get(id=approval_id)
    approval.is_approved = True
    approval.approved_by = manager
    approval.approved_at = timezone.now()
    approval.save()

#  ==============eND======================================

# FIXME  ======================== SHOPPING CART ==============



def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def remove_cart(request, cart_item_id):
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(cart=cart, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except:
        pass
    return redirect('cart')


def update_cart(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get( user=request.user, id=cart_item_id)
        cart_item.quantity += 1
        cart_item.save()
    except:
        pass
    return redirect('cart')


def remove_cart_item(request, cart_item_id):
  
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(user=request.user, id=cart_item_id)
    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get( cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')



def cart(request, total=0, quantity=0, cart_items=None):
    try:
        grand_total = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += cart_item.sub_total()
            quantity += cart_item.quantity

        grand_total = total
    except ObjectDoesNotExist:
        pass  # just ignore

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'grand_total': grand_total,
    }
    return render(request, 'cart/cart.html', context)


@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):
    total_discount = 0
    grand_total = 0
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += cart_item.sub_total()
            quantity += cart_item.quantity
            total_discount += calculate_total_discount(cart_item)
    except ObjectDoesNotExist:
        pass 
    print(total_discount)
    grand_total = total - total_discount
    context = {
        'total_discount': total_discount,
        'grand_total':grand_total,
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
    }
    return render(request, 'cart/checkout.html', context)



def add_cart(request, product_id):
    current_user = request.user
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        selected_variations_id = request.POST.get('variation')
        # selected_variations = Variation.objects.filter(id__in=selected_variations_ids)
        
        try:
            # Get the matching ProductVariation based on the selected variations
            # product_variation = ProductVariation.objects.filter(product=product, variations__in=selected_variations).distinct().first()
            product_variation = ProductVariation.objects.filter(product=product, id=int(selected_variations_id)).first()
            if product_variation:
                is_cart_item_exists = CartItem.objects.filter(product=product, user=current_user, product_variation=product_variation).exists()

                if is_cart_item_exists:
                    cart_item = CartItem.objects.get(product=product, user=current_user, product_variation=product_variation)
                    cart_item.quantity += 1
                    cart_item.save()
                else:
                    cart_item = CartItem.objects.create(
                        product=product,
                        product_variation=product_variation,
                        quantity=1,
                        user=current_user,
                    )
                    cart_item.save()

            else:
                # Handle the case where no matching ProductVariation is found
                messages.error(request, "This combination of variations is not available.")
                return redirect('show_single_product', product_id=product_id)

        except ProductVariation.DoesNotExist:
            messages.error(request, "Please select valid product variations.")
            return redirect('show_single_product', product_id=product_id)

    return redirect('cart')

    

def get_variation_price(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        selected_variations_ids = request.POST.getlist('variations[]')
        
        # Get the selected variations
        selected_variations = Variation.objects.filter(id__in=selected_variations_ids)
        
        # Find the matching ProductVariation with the selected variations
        try:
            product_variation = ProductVariation.objects.filter(product=product, variations__in=selected_variations).distinct().first()

            if product_variation:
                # Return the price of the matched ProductVariation
                return JsonResponse({'price': product_variation.price}, status=200)
            else:
                # Handle case where no product variation is found
                return JsonResponse({'error': 'No matching product variation found'}, status=404)
        
        except ProductVariation.DoesNotExist:
            return JsonResponse({'error': 'Invalid variations selected'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


# ====================eND==============================