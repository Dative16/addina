from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
import pandas as pd
from carts.models import CartItem
import datetime
from .models import Order, Payment, OrderProduct
from .forms import PymentForm, DateRangeForm
import json
from store.models import Product, Shop, ProductVariation
from django.contrib import messages
from datetime import timedelta, date
from django.utils import timezone
from django.db.models import Sum

from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, ExtractMonth, TruncYear


def payments(request, order_number):
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=order_number)
    yr = int(datetime.date.today().strftime('%Y'))
    dt = int(datetime.date.today().strftime('%d'))
    mt = int(datetime.date.today().strftime('%m'))
    d = datetime.date(yr, mt, dt)
    current_date = d.strftime("%Y%m%d")
    try:
        if request.method == 'POST':
            pyment_slip = request.POST['payment_slip']
            pyment_method = request.POST['payment_methods']
            payment_id = request.POST['payment_id']

            payment = Payment()
            payment.user=request.user
            payment.payment_id=payment_id
            payment.payment_method=pyment_method
            payment.pyment_slip = pyment_slip
            payment.amount_paid=order.order_total
            payment.status='Paid'
            payment.save()
            order.payment = payment
            order.is_ordered = True
            order.status = "Penging"
            order.save()
           
        else:
            payment = Payment()
            payment.user=request.user
            payment.payment_method="Cash In Hand"
            payment.amount_paid=order.order_total
            payment.save()
            payment.payment_id=current_date + str(request.user.id) + str(payment.id)
            payment.status='Paid'
            payment.save()

            order.payment = payment
            order.is_ordered = True
            order.status = "Pending"
            order.save()
            
        # Move the cart items to Order Product table
        cart_items = CartItem.objects.filter(user=request.user)

        for item in cart_items:
            orderproduct = OrderProduct()
            orderproduct.order_id = order.id
            orderproduct.payment = payment
            orderproduct.user_id = request.user.id
            orderproduct.product_id = item.product_id
            orderproduct.branch_id = order.branch.id
            orderproduct.quantity = item.quantity
            orderproduct.product_price = item.product.price
            orderproduct.variations = item.product_variation
            orderproduct.ordered = True
            orderproduct.save()

            product = Product.objects.get(id=item.product_id)
            Product_variation = ProductVariation.objects.get(id=item.product_variation.id)
            Product_variation.stock -= item.quantity
            product.stock -= item.quantity
            product.save()

        CartItem.objects.filter(user=request.user).delete()
        messages.success(request, 'The Payment Has Been Confirmed\nYou Can Not Edit These After Has Been Cornfimed!')
        return redirect('store')
    except Exception as e:
        messages.error(request, f'{e}')
    context = {
        'order': order
    }

    return render(request, 'order/payments.html', context)


def place_order(request, total=0, quantity=0, ):
    current_user = request.user
    shop_branch = Shop.objects.filter(user=current_user).first()


    # If the cart count is less than or equal to 0, then redirect back to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    total_discount = 0
    back_track = []
    cart_item_ids = []
    for cart_item in cart_items:
        total += cart_item.sub_total() 
        quantity += cart_item.quantity
        total_discount += cart_item.discount_amount
        back_track.append({
            'product_id': cart_item.product.id,
            "product_name": cart_item.product.product_name,
            "product_price":str(cart_item.product.price),
            "product_variation_id":cart_item.product_variation.id,
            "Product_variation_sub_total": str(cart_item.product_variation.sub_total),
            "cart_item_id": cart_item.id,
            "quantity": str(cart_item.quantity),
            "sub_total": str(cart_item.sub_total()),
            'discount_amount': cart_item.discount_amount
        })
        cart_item_ids.append(cart_item.id)

    grand_total = total - total_discount
    back_track.append({"Grand_Total":str(grand_total- total_discount)})
    back_track.append({"cart_item_ids":cart_item_ids})
    print(back_track)
    data = Order()
    data.user = current_user
    data.branch_id = shop_branch.id
    data.discount_amount = total_discount
    data.order_total = grand_total 
    data.ip = request.META.get('REMOTE_ADDR')
    data.back_track = json.dumps(back_track)
    data.save()
    # Generate order number
    yr = int(datetime.date.today().strftime('%Y'))
    dt = int(datetime.date.today().strftime('%d'))
    mt = int(datetime.date.today().strftime('%m'))
    d = datetime.date(yr, mt, dt)
    current_date = d.strftime("%Y%m%d")  # 20240929
    order_number = current_date + str(data.id)
    data.order_number = order_number
    data.save()
    messages.success(request, 'Order Has Been Created Successfuly!\nPlease Confrim Payment for Safety records!')
    messages.error(request, "Please Confirm Order Payment Before Creating Another To Avoid Conflit!")
    order = Order.objects.get(user=request.user, order_number=order_number)
    context = {
        'order': order
    }
    return render(request, 'order/payments.html', context)


def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = order.order_total

        payment = Payment.objects.get(payment_id=transID)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'order/order_complete.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')


# Analytics section

def analytics(request):
    shop = Shop.objects.filter(user=request.user).first()
    most_selling = (
        OrderProduct.objects
        .filter(created_at__gte=timezone.now() - timedelta(days=30),branch=shop)
        .values('product__product_name')
        .annotate(total_sold=Count('id'))
        
    )
    labels = [item['product__product_name'] for item in most_selling]
    data = [item['total_sold'] for item in most_selling]

    today = timezone.now().date()
    last_week_orders = (
        Order.objects.filter(created_at__gte=today - timedelta(days=7),branch_id=shop.id,is_ordered=True)
        .annotate(day=TruncDay('created_at')) 
        .values('day')
        .annotate(daily_profit=Sum('order_total'))
        .order_by('day')
    )
    labels_weekly = [item['day'].strftime('%A') for item in last_week_orders]
    data_weekly = [item['daily_profit'] for item in last_week_orders]

    monthly_orders = (
    Order.objects.filter(created_at__gte=today - timedelta(days=30), branch_id=shop.id,is_ordered=True)  
    .annotate(day=TruncDay('created_at')) 
    .values('day')
    .annotate(weekly_profit=Sum('order_total')) 
    .order_by('day')
    )

    labels_week = [item['day'].strftime('%d %b %Y') for item in monthly_orders]
    data_week = [item['weekly_profit'] for item in monthly_orders]

    monthls_orders = (
    Order.objects.filter(created_at__gte=today - timedelta(days=182), branch_id=shop.id,is_ordered=True)  
    .annotate(month=TruncMonth('created_at')) 
    .values('month')
    .annotate(month_profit=Sum('order_total')) 
    .order_by('month')
    )
    print(monthls_orders)

    labels_month = [item['month'].strftime('%B') for item in monthls_orders]
    data_month = [item['month_profit'] for item in monthls_orders]

    return render(request, 'order/analytics.html', {
        'labels': labels,
        'data': data,
        'labels_weekly':labels_weekly,
        'data_weekly': data_weekly,
        'labels_week': labels_week,
        'data_week':data_week,
        'labels_month': labels_month,
        'data_month': data_month,
    })


def get_inconplete_orders(request):
    shop = Shop.objects.filter(user=request.user).first()
    orders = Order.objects.filter(branch_id=shop.id, status='New')
    return render(request, 'order/incomplete_orders.html', {
        'orders':orders
    })

def confirm_incomplete_order(request, order_number):
    shop = Shop.objects.filter(user=request.user).first()
    order = Order.objects.filter(branch_id=shop.id, status='New', order_number=order_number).first()
    data = json.loads(order.back_track)
    print(data)

    yr = int(datetime.date.today().strftime('%Y'))
    dt = int(datetime.date.today().strftime('%d'))
    mt = int(datetime.date.today().strftime('%m'))
    d = datetime.date(yr, mt, dt)
    current_date = d.strftime("%Y%m%d")
    pyment_number = str(current_date) +"$"+ order.order_number
    try:
        payment = Payment()
        payment.user=request.user
        payment.payment_method="Cash In Hand"

        payment.amount_paid=float(data[-2]['Grand_Total'])
        payment.save()
        payment.payment_id= pyment_number
        payment.status='Paid'
        payment.save()

        order.payment = payment
        order.is_ordered = True
        order.status = "Completed"
        order.save()

        print(data[:-2])
        for item in data[:-2]:
            orderproduct = OrderProduct()
            orderproduct.order_id = order.id
            orderproduct.payment = payment
            orderproduct.user_id = request.user.id
            orderproduct.product_id = int(item['product_id'])
            orderproduct.branch_id = order.branch.id
            orderproduct.quantity = int(item['quantity'])
            orderproduct.product_price = float(item['product_price'])

            Product_variation = ProductVariation.objects.get(id=int(item['product_variation_id']))

            orderproduct.variations = Product_variation
            orderproduct.ordered = True
            orderproduct.save()

            product = Product.objects.get(id=int(item['product_id']))
            Product_variation.stock -= int(item['quantity'])
            product.stock -= int(item['quantity'])
            product.save()
        messages.success(request, 'The order Has Been Confirmed Successfuly')

        return redirect('home')
    except Exception as e:
        print(e)
        messages.error(request, str(e))
        return redirect('get_inconplete_orders')
    


# FIXME ========================= Downloads CSV Files ==================== 

def download_daily_orders(request):
    shop = Shop.objects.get(user=request.user)
    today = timezone.now().date()
    orders = Order.objects.filter(created_at__date=today, branch_id=shop.id)

    # Create a DataFrame
    df = pd.DataFrame(list(orders.values()))

    # Generate CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="daily_orders_{today}.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def download_weekly_orders(request):
    shop = Shop.objects.get(user=request.user)
    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday())
    orders = Order.objects.filter(created_at__date__gte=week_start, branch_id=shop.id)

    df = pd.DataFrame(list(orders.values()))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="weekly_orders_{week_start}.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def download_monthly_orders(request):
    shop = Shop.objects.get(user=request.user)
    today = timezone.now().date()
    month_start = today.replace(day=1)
    orders = Order.objects.filter(created_at__date__gte=month_start, branch_id=shop.id)

    df = pd.DataFrame(list(orders.values()))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="monthly_orders_{month_start}.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def download_annual_orders(request):
    shop = Shop.objects.get(user=request.user)
    today = timezone.now().date()
    year_start = today - timezone.timedelta(days=365)
    orders = Order.objects.filter(created_at__date__gte=year_start, branch_id=shop.id)

    df = pd.DataFrame(list(orders.values()))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="annual_orders.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def download_all_orders(request):
    shop = Shop.objects.get(user=request.user)
    orders = Order.objects.filter(branch_id=shop.id)

    df = pd.DataFrame(list(orders.values()))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_orders.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response


def download_views(request):
    shop = Shop.objects.get(user=request.user)
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            orders = Order.objects.filter(created_at__date__range=(start_date, end_date), branch_id=shop.id)

            # Create a DataFrame
            df = pd.DataFrame(list(orders.values()))

            # Generate CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="daily_orders_{start_date}_to_{end_date}.csv"'
            df.to_csv(path_or_buf=response, index=False)

            return response
    else:
        form = DateRangeForm()
    
    return render(request, 'base/download_views.html', {'form': form})



# for admin


def download_daily_orders_admin(request, shop_id):
    shop = Shop.objects.get(id=shop_id)
    today = timezone.now().date()
    orders = Order.objects.filter(created_at__date=today, branch_id=shop.id)

    # Create a DataFrame
    df = pd.DataFrame(list(orders.values()))

    # Generate CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="daily_orders_{today}.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def download_weekly_orders_admin(request, shop_id):
    shop = Shop.objects.get(id=shop_id)
    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday())
    orders = Order.objects.filter(created_at__date__gte=week_start, branch_id=shop.id)

    df = pd.DataFrame(list(orders.values()))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="weekly_orders_{week_start}.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def download_monthly_orders_admin(request, shop_id):
    shop = Shop.objects.get(id=shop_id)
    today = timezone.now().date()
    month_start = today.replace(day=1)
    orders = Order.objects.filter(created_at__date__gte=month_start, branch_id=shop.id)

    df = pd.DataFrame(list(orders.values()))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="monthly_orders_{month_start}.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def download_annual_orders_admin(request):
    shop = Shop.objects.get(user=request.user)
    today = timezone.now().date()
    year_start = today - timezone.timedelta(days=365)
    orders = Order.objects.filter(created_at__date__gte=year_start, branch_id=shop.id)

    df = pd.DataFrame(list(orders.values()))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="annual_orders.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response

def download_all_orders_admin(request, shop_id):
    shop = Shop.objects.get(id=shop_id)
    orders = Order.objects.filter(branch_id=shop.id)

    df = pd.DataFrame(list(orders.values()))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_orders.csv"'
    df.to_csv(path_or_buf=response, index=False)

    return response


def download_views_admin(request,shop_id):
    shop = Shop.objects.get(id=shop_id)
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            orders = Order.objects.filter(created_at__date__range=(start_date, end_date), branch_id=shop.id)

            # Create a DataFrame
            df = pd.DataFrame(list(orders.values()))

            # Generate CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="daily_orders_{start_date}_to_{end_date}.csv"'
            df.to_csv(path_or_buf=response, index=False)

            return response
    else:
        form = DateRangeForm()
    
    return render(request, 'base/download_views_admin.html', {'form': form, 'shop':shop})