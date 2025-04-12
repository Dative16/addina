from django.urls import path
from . import views

urlpatterns = [
    path('store/', views.store, name='store'),
    path('create_shop/', views.create_shop, name='create_shop'),
    path('category/<slug:category_slug>/', views.store, name='product_by_category'),
    path('search/', views.search, name='search'),
    path('show_single_product/<int:product_id>/', views.show_single_product, name='show_single_product'),
    path('create_product/', views.create_product, name='create_product'),
    path('update_product/<int:product_id>/', views.edit_product, name='update_product'),
    path('create_variation_category/', views.create_variation_category, name='create_variation_category'),
    path('create_variation/',views.create_variation, name='create_variation'),
    path('create_product_variation/', views.create_product_variation, name='create_product_variation'),
]