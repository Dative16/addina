
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta
from django.utils import timezone
from accounts.models import Account
from carts.models import DiscountRule
from .models import Category,Product, ProductGallery, ReviewRating, Shop, Variation, VariationCategory, ProductVariation
from orders.models import Order
from django.contrib import messages
from .forms import ProductForm, ProductVariationForm
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.timezone import now
from django.core.mail import EmailMessage

from django.db.models import Sum

from django.http import HttpResponse, JsonResponse
import pandas as pd

from django.views.generic import CreateView, UpdateView, ListView, DetailView, DeleteView
from .models import Product
from .forms import ProductForm, DynamicCategoryForm
from django.urls import reverse_lazy
from django.http import JsonResponse
from .models import VariationCategory, Variation, ProductVariation


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

@login_required(login_url='accounts/login')
def create_shop(request):
    if request.method == 'POST':   
        name = request.POST['name']
        location = request.POST['location']
        shop = Shop.objects.create(name=name, location=location, user=request.user)
        shop.save()
        messages.success(request, "Your Shop Branch as Been created!")
        return redirect('home')
    
    return render(request, 'store/create_shop.html')


class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/create_product.html'
    success_url = reverse_lazy('product_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You need to login first")
            return redirect('login')
            
        if not request.user.shops.exists():
            messages.warning(request, 'You need to create a shop first')
            return redirect('shop_create')
            
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, 
                f"Product '{self.object.product_name}' created successfully!"
            )
            return response
        except Exception as e:
            messages.error(self.request, f"Error creating product: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, 
            "Please correct the errors below"
        )
        return super().form_invalid(form)

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/create_product.html'


class ShopCreateView(CreateView):
    model = Shop
    fields = ['name', 'location', 'description']
    template_name = 'store/shop_form.html'
    
    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            return redirect('login')
            
        # Check if shop name already exists
        if Shop.objects.filter(name__iexact=form.cleaned_data['name']).exists():
            form.add_error('name', 'Shop with this name already exists')
            return self.form_invalid(form)
            
        shop = form.save(commit=False)
        shop.user = self.request.user
        shop.save()
        
        messages.success(self.request, 'Shop created successfully!')
        return redirect('product_create')


class ShopUpdateView(UpdateView):
    model = Shop
    fields = ['name', 'location', 'description']
    template_name = 'store/shop_form.html'
    
    def get_queryset(self):
        return Shop.objects.filter(user=self.request.user)

def category_autocomplete(request):
    """Handle AJAX requests for category suggestions"""
    search = request.GET.get('search', '')
    categories = Category.objects.filter(
        category_name__icontains=search
    )[:10]
    
    results = [{
        'id': cat.id,
        'category_name': cat.category_name,
        'parent': {'id': cat.parent.id, 'category_name': cat.parent.category_name} if cat.parent else None
    } for cat in categories]
    
    return JsonResponse(results, safe=False)

class CategoryCreateView(CreateView):
    model = Category
    form_class = DynamicCategoryForm
    template_name = 'store/create_category.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Category "{self.object.category_name}" created successfully')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Error creating category. Please check the form.')
        return super().form_invalid(form)

class CategoryUpdateView(UpdateView):
    model = Category
    form_class = DynamicCategoryForm
    template_name = 'store/create_category.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Category "{self.object.category_name}" updated successfully')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Error updating category. Please check the form.')
        return super().form_invalid(form)

def category_list(request):
    """View to list all categories"""
    categories = Category.objects.all().prefetch_related('parent')
    return render(request, 'store/category_list.html', {
        'categories': categories
    })



class VariationCategoryCreateView(CreateView):
    model = VariationCategory
    fields = ['name']
    template_name = 'store/variation_category_form.html'
    success_url = reverse_lazy('variation_category_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'id': self.object.id,
                'name': self.object.name
            })
        return response

class VariationCategoryListView(ListView):
    model = VariationCategory
    template_name = 'store/variation_category_list.html'
    context_object_name = 'categories'

class VariationCreateView(CreateView):
    model = Variation
    fields = ['variation_category', 'variation_value', 'is_active']
    template_name = 'store/variation_form.html'
    success_url = reverse_lazy('variation_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = VariationCategory.objects.all()
        return context

class VariationListView(ListView):
    model = Variation
    template_name = 'store/variation_list.html'
    context_object_name = 'variations'

class ProductVariationCreateView(CreateView):
    model = ProductVariation
    fields = ['product', 'variations', 'price', 'stock', 'is_active']
    template_name = 'store/product_variation_form.html'
    success_url = reverse_lazy('product_variation_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
        context['variations'] = Variation.objects.filter(is_active=True)
        return context

class ProductVariationListView(ListView):
    model = ProductVariation
    template_name = 'store/product_variation_list.html'
    context_object_name = 'product_variations'

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
    return render(request, 'store/product-details.html', context)



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


class ProductListView(ListView):
    model = Product
    template_name = 'store/adm_product_list.html'
    context_object_name = 'products'
    paginate_by = 10
    
    def get_queryset(self):
        shop = Shop.objects.get(user=self.request.user)
        queryset = super().get_queryset()
        # Filter products by the user's shop (assuming shop is linked to user)
        queryset = queryset.filter(shop=shop)
        
        # Add search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(product_name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__category_name__icontains=search_query)
            )
        return queryset.order_by('-modified_date')

    def get_context_data(self, **kwargs):
        shop = Shop.objects.get(user=self.request.user)
        context = super().get_context_data(**kwargs)
        # Add search query to context
        context['search_query'] = self.request.GET.get('search', '')
        # Add counts for dashboard
        context['total_products'] = Product.objects.filter(shop=shop).count()
        context['active_products'] = Product.objects.filter(shop=shop, is_available=True).count()
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/adm_product_detail.html' 
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['variations'] = ProductVariation.objects.filter(product=self.object)
        context['reviews'] = ReviewRating.objects.filter(product=self.object)
        context['gallery'] = ProductGallery.objects.filter(product=self.object)
        return context

class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'store/product_confirm_delete.html'
    success_url = reverse_lazy('product_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Product deleted successfully")
        return super().delete(request, *args, **kwargs)






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