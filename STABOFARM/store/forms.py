from django import forms
from .models import Product, Shop, VariationCategory, Variation, ProductVariation, ReviewRating, ProductGallery, Category
from django.utils.text import slugify


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['shop', 'product_name', 'category', 'description', 
                 'price', 'image', 'stock', 'expire_date', 
                 'buy_price', 'is_available']
        widgets = {
            'expire_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['shop'].queryset = Shop.objects.filter(user=self.user)
            self.fields['shop'].required = True
            self.fields['shop'].empty_label = "Select Your Shop"

    def clean_shop(self):
        shop = self.cleaned_data.get('shop')
        if shop and shop.user != self.user:
            raise forms.ValidationError("You don't own this shop")
        return shop

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock < 0:
            raise forms.ValidationError("Stock cannot be negative")
        return stock

class VariationCategoryForm(forms.ModelForm):
    class Meta:
        model = VariationCategory
        fields = ['name']

class VariationForm(forms.ModelForm):
    class Meta:
        model = Variation
        fields = ['variation_category', 'variation_value', 'is_active']

class ProductVariationForm(forms.ModelForm):
    class Meta:
        model = ProductVariation
        fields = ['product', 'variations', 'price', 'stock', 'is_active']
        widgets = {
            'variations': forms.CheckboxSelectMultiple(),
        }

class ReviewRatingForm(forms.ModelForm):
    class Meta:
        model = ReviewRating
        fields = ['subject', 'review', 'rating']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'step': 0.5}),
        }

class ProductGalleryForm(forms.ModelForm):
    class Meta:
        model = ProductGallery
        fields = ['image']
        
class DynamicCategoryForm(forms.ModelForm):
    new_category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Type to search or create new category',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Category
        fields = ['parent', 'category_name']
        widgets = {
            'category_name': forms.HiddenInput(),
            'parent': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category_name'].required = False

    def clean(self):
        cleaned_data = super().clean()
        new_category = cleaned_data.get('new_category')
        existing_category = cleaned_data.get('category_name')

        if not existing_category and not new_category:
            raise forms.ValidationError("Category is required")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        new_category = self.cleaned_data.get('new_category')
        
        if new_category:
            category, created = Category.objects.get_or_create(
                category_name__iexact=new_category.strip(),
                defaults={
                    'category_name': new_category.strip(),
                    'slug': slugify(new_category.strip())
                }
            )
            instance = category
        if commit:
            instance.save()
        return instance