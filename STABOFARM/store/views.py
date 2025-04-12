
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta
from django.utils import timezone
from accounts.models import Account
from carts.models import DiscountRule
from .models import Category,Product, Shop, Variation, VariationCategory, ProductVariation
from orders.models import Order
from django.contrib import messages
from .forms import ProductForm, ProductEditForm, ProductVariationForm
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.timezone import now
from django.core.mail import EmailMessage

from django.db.models import Sum

from django.http import HttpResponse
import pandas as pd

@login_required(login_url='login')
def store(request, category_slug=None):
    shop = Shop.objects.get(user=request.user)
    categories = None
    products = None

    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True, shop_id=shop.id, stock__gt=0)
        print(products[0].created_date)
        paginator = Paginator(products, 15)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()
    else:
        products = Product.objects.all().filter(is_available=True, shop_id=shop.id, stock__gt=0) #.order_by('id')
        paginator = Paginator(products, 15)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()

    context = {
        'products': paged_products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)



def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.filter(
                Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()
    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)

@login_required(login_url='login')
def create_shop(request):
    if request.method == 'POST':   
        name = request.POST['name']
        location = request.POST['location']
        shop = Shop.objects.create(name=name, location=location, user=request.user)
        shop.save()
        messages.success(request, "Your Shop Branch as Been created!")
        return redirect('home')
    
    return render(request, 'store/create_shop.html')

@login_required(login_url='login')
def create_product(request):
    categories = Category.objects.all()
    form = ProductForm()
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # image = form.cleaned_data['image']
            product_name = form.cleaned_data['product_name']
            price = form.cleaned_data['price']
            stock  = form.cleaned_data['stock']
            expire_date = form.cleaned_data['expire_date']
            buy_price  = form.cleaned_data['buy_price']
            description = form.cleaned_data['description']
           
            image = request.FILES.get('image')
            print("Uploaded Image:",image)
            input_category = request.POST['category']

            category = Category.objects.get_or_create(category_name=input_category)
        
            shop = Shop.objects.get(user=request.user)
            print(category)
            product = Product.objects.create(product_name=product_name, shop=shop, description=description, 
                                            price=price, image=image, stock=stock, category=category[0], buy_price=buy_price, expire_date=expire_date)
            product.save()
            messages.success(request, 'Product has been created Successful')
            return redirect('home')
    context = {
        'form': form,
        'categories': categories,
    }
    return render(request, 'store/create_product.html', context)

def edit_product(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        form = ProductEditForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product Has been Updated.')
            return redirect('store')
    else:

        form = ProductEditForm(instance=product)
    context={
        'form':form,
        'product': product,
    }
    return render(request, 'store/update_product.html', context)


def select_shop(request):
    shops = Shop.objects.all()
    if request.method == 'POST':
        shop = request.POST['shop']
        selected_shop = Shop.objects.get(name=shop)
        selected_shop.user = request.user
        selected_shop.save()
        return redirect('home')
    return render(request, 'store/create_shop.html', {
        'shops': shops,
    })


def create_variation_category(request):
    if request.method == 'POST':
        category = request.POST['category']
        variation_category = VariationCategory.objects.create(name=category)
        variation_category.save()
        messages.success(request, 'Variation Category Added!')

        return redirect('store')
    return render(request, 'store/create_variation_category.html')


def create_variation(request):
    products = Product.objects.all()
    variation_categories = VariationCategory.objects.all()
    if request.method == 'POST':

        variation_value = request.POST['variation_value']
        category = request.POST['category']
        category = VariationCategory.objects.get_or_create(name=category)

        print(category)


        variation = Variation.objects.create( variation_category=category[0], variation_value=variation_value)
        variation.save()
        messages.success(request, 'Variation Has Been Added!')
        return redirect('store')
    
    context = {
        'products': products,
        'varitions_categories': variation_categories,
    } 
    return render(request, 'store/create_variation.html', context)

def create_product_variation(request):
    shop = Shop.objects.get(user=request.user)
    if request.method == 'POST':
        form = ProductVariationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product Variation Added Successfuly!')
            return redirect('store')
    else:
        form = ProductVariationForm()
    context = {
        'form': form,
    }
    return render(request, 'store/create_product_variation.html', context)



def show_single_product(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        print(product.image.url)
        product_variation = ProductVariation.objects.filter(product=product)
    except:
        pass

    context = {
        'product': product,
        'product_variation':product_variation,
        }
    return render(request, 'store/single_product.html', context)



def expire_soon_products(request):
    shop = Shop.objects.get(user=request.user)
    today = timezone.now().date()
    thirty_days_later = today + timedelta(days=30)

    expiring_products = Product.objects.filter(
            shop_id= shop.id,
            expire_date__isnull=False,
            expire_date__lte=thirty_days_later,
            expire_date__gte=today
        )
    
    paginator = Paginator(expiring_products, 15)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)
    
    context = {
        'products': paged_products
    }
    return render(request, 'store/expiring_products.html', context)



# def send_email_to_admins_for_purchases(request, purchase_request,):
#     shop = Shop.objects.get(user=request.user)
#     today = date.today()
#     products = Product.objects.filter(
#         shop_id=shop.id,
#         expire_date__isnull=False,  
#         expire_date__lte=today + timedelta(days=30),  # Expiring in less than 30 days
#     ) | Product.objects.filter(
#         stock__lt=20,  # Stock less than 20
#         shop_id=shop.id,
#     )
#     if products.exists():
#         pdf_buffer = generate_pdf(products)
#         # Get all admin users
#         admin_users = get_user_model().objects.filter(is_superuser=True)
#         admin_emails = [admin.email for admin in admin_users if admin.email]
        
#         if admin_emails:
#             subject = f"Purchase Request from {purchase_request.employee.username}"
#             message = f"""
#             A purchase request has been made by {purchase_request.employee.username}.
#             Amount: {purchase_request.amount}
#             Reason: {purchase_request.reason}
#             Please log in to the system to review and approve/reject this request.
#             """
#             email = EmailMessage(
#                     subject,
#                     message,
#                     settings.DEFAULT_FROM_EMAIL,
#                     admin_emails
#                 )
                
#                 # Attach the PDF
#             email.attach('Products_Near_Expiry_Or_Low_Stock_Report.pdf', pdf_buffer.getvalue(), 'application/pdf')
            
#             # Send the email
#             email.send()

#     else:
#         admin_users = get_user_model().objects.filter(is_superuser=True)
#         admin_emails = [admin.email for admin in admin_users if admin.email]
#         if admin_emails:
#             subject = f"Purchase Request from {purchase_request.employee.username}"
#             message = f"""
#             A purchase request has been made by {purchase_request.employee.username}.
#             Amount: {purchase_request.amount}
#             Reason: {purchase_request.reason}
#             Please log in to the system to review and approve/reject this request.
#             """
#             send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, admin_emails)


# def make_purchase_request(request):
#     shop = Shop.objects.get(user=request.user)
#     if request.method == 'POST':
#         amount = request.POST.get('amount')
#         reason = request.POST.get('reason')
        
#         purchase_request = PurchasesRequest.objects.create(
#             employee=request.user,
#             amount=amount,
#             reason=reason,
#             shop=shop
#         )
#         purchase_request.save()
#         AuditLog.objects.create(
#             shop=shop,
#             user=request.user,
#             action_type='Admin Confirmation',
#             description=f"Weiting Approval for {purchase_request.amount}TZsh Request.",)
        
#         messages.success(request, 'Your request has been submitted successfully.')
#         try:
#             send_email_to_admins_for_purchases(request, purchase_request)
#         except: 
#             pass

#         return redirect('home') 
    
#     return render(request, 'store/make_purchase_request.html')



# def send_confirmation_notification(employee, purchase_request, action):
#     message = f"Your purchase request for {purchase_request.amount} has been {action}."
    
#     # Assuming you have a Notification model for in-app notifications
#     Notification.objects.create(user=employee, message=message)

#     # Send email notification to the employee
#     send_mail(
#         'Purchase Request Update',
#         message,
#         settings.DEFAULT_FROM_EMAIL,
#         [employee.email]
#     )

# def manage_purchase_requests(request, purchase_id):
    
#     # Only admin can access this
#     if not request.user.is_superuser:
#         return redirect('home')

#     pending_requests = PurchasesRequest.objects.filter(status='Pending', id=purchase_id).first()
#     if request.method == 'POST':
#         action = request.POST.get('action')  # 'approve' or 'reject'
#         purchase_request = PurchasesRequest.objects.get(id=purchase_id)

#         if action == 'approve':
#             purchase_request.status = 'Approved'
#             purchase_request.approved_by = request.user
#             purchase_request.approved_at = now()
#             purchase_request.save()

#             DailyExpense.objects.create(
#                 shop_id=purchase_request.shop.id,
#                 amount=purchase_request.amount,
#                 description=purchase_request.reason
#             ).save()

#             AuditLog.objects.create(
#                 shop_id=purchase_request.shop.id,
#                 user=request.user,
#                 action_type='Purchase Request',
#                 description=f"Approved request for {purchase_request.amount}",)

#             # Send notification to the employee
#             send_confirmation_notification(purchase_request.employee, purchase_request, 'approved')
#             return redirect('view_expenses')

#         elif action == 'reject':
#             purchase_request.status = 'Rejected'
#             purchase_request.save()

#             # Send notification to the employee
#             send_confirmation_notification(purchase_request.employee, purchase_request, 'rejected')

#         return redirect('view_expenses')

#     return render(request, 'store/manage_purchase_requests.html', {'pending_request': pending_requests})

# #  FIXME ================Notification section===================


# def notify_user(user, message):
#     Notification.objects.create(user=user, message=message)

# @receiver(post_save, sender=DiscountRule)
# def send_discount_notification(sender, instance, created, **kwargs):
#     if created:
#         users = Account.objects.all()
#         for user in users:
#             Notification.objects.create(user=user, message=f"New discount on {instance.name}")



# # FIXME ======================= Downloads Csv files ==========================

# def download_low_stock_products(request):
#     shop = Shop.objects.get(user=request.user)
#     products = Product.objects.filter(stock__lt=20, shop_id=shop.id)

#     df = pd.DataFrame(list(products.values()))

#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = 'attachment; filename="low_stock_products.csv"'
#     df.to_csv(path_or_buf=response, index=False)

#     return response


# def download_expiring_products(request):
#     shop = Shop.objects.get(user=request.user)
#     today = timezone.now().date()
#     products = Product.objects.filter(expire_date__isnull=False, expire_date__lte=today + timezone.timedelta(days=30), shop_id=shop.id)

#     df = pd.DataFrame(list(products.values()))

#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = 'attachment; filename="expiring_products.csv"'
#     df.to_csv(path_or_buf=response, index=False)

#     return response

# def download_all_products(request):
#     shop = Shop.objects.get(user=request.user)
#     products = Product.objects.filter(shop=shop)

#     df = pd.DataFrame(list(products.values()))

#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = 'attachment; filename="all_products.csv"'
#     df.to_csv(path_or_buf=response, index=False)

#     return response


# # day to day expenses
# def view_expenses(request):
#     shop = Shop.objects.get(user=request.user)
#     expenses = DailyExpense.objects.filter(shop=shop)
#     if request.method == 'POST':
#         amount = request.POST['amount']
#         description = request.POST['description']

#         DailyExpense.objects.create(
#             shop=shop,
#             amount=amount,
#             description=description
#         ).save()
#         return redirect('view_expenses')
#     return render(request, 'store/view_expenses.html', {'expenses':expenses})




# # Admin:

# def download_low_stock_products_admin(request, shop_id):
#     shop = Shop.objects.get(id=shop_id)
#     products = Product.objects.filter(stock__lt=20, shop_id=shop.id)

#     df = pd.DataFrame(list(products.values()))

#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = 'attachment; filename="low_stock_products.csv"'
#     df.to_csv(path_or_buf=response, index=False)

#     return response


# def download_expiring_products_admin(request, shop_id):
#     shop = Shop.objects.get(id=shop_id)
#     today = timezone.now().date()
#     products = Product.objects.filter(expire_date__isnull=False, expire_date__lte=today + timezone.timedelta(days=30), shop_id=shop.id)

#     df = pd.DataFrame(list(products.values()))

#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = 'attachment; filename="expiring_products.csv"'
#     df.to_csv(path_or_buf=response, index=False)

#     return response

# def download_all_products_admin(request, shop_id):
#     shop = Shop.objects.get(id=shop_id)
#     products = Product.objects.filter(shop=shop)

#     df = pd.DataFrame(list(products.values()))

#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = 'attachment; filename="all_products.csv"'
#     df.to_csv(path_or_buf=response, index=False)

#     return response