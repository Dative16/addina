from django.urls import path
from . import views
urlpatterns = [
    path('store/', views.store, name='store'),
    path('create_shop/', views.create_shop, name='create_shop'),
    path('category/<slug:category_slug>/', views.store, name='product_by_category'),
    path('search/', views.search, name='search'),
    path('show_single_product/<int:product_id>/', views.show_single_product, name='show_single_product'),
    
    path('products/new/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('api/categories/', views.category_autocomplete, name='category_autocomplete'),
    
    path('variation-categories/', views.VariationCategoryListView.as_view(), name='variation_category_list'),
    path('variation-categories/new/', views.VariationCategoryCreateView.as_view(), name='variation_category_create'),
    path('variations/', views.VariationListView.as_view(), name='variation_list'),
    path('variations/new/', views.VariationCreateView.as_view(), name='variation_create'),
    path('product-variations/', views.ProductVariationListView.as_view(), name='product_variation_list'),
    path('product-variations/new/', views.ProductVariationCreateView.as_view(), name='product_variation_create'),
    
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('shop/create/', views.ShopCreateView.as_view(), name='shop_create'),
]