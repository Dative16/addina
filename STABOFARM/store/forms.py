from typing import Any
from .models import Shop, Product, Category, ProductVariation
from django import forms

class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ['name', 'location']


    def clean(self):
        cleaned_data = super(ShopForm, self).clean()

class ProductForm(forms.ModelForm):
    # image = forms.ImageField(required=False, error_messages={'invalid': ("Image files only")}, widget=forms.FileInput)
    description = forms.CharField(required=False, error_messages={"Required": ("This field is Required")}, widget=forms.Textarea(attrs={
        'placeholder': 'eg. Product descriptions'}
    ))
    expire_date = forms.DateField(required=False, error_messages={"Required": ("date formart must be of YYYY-MM-DD")}, widget=forms.DateInput(attrs={
        "placeholder": "eg. 2024-09-28 (YYYY-MM-DD)", 'type': 'date'
    }))
    class Meta:
        model = Product
        fields = ['product_name', 'price', 'stock','buy_price']
    
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['product_name'].widget.attrs['placeholder'] = 'eg. Samsung Galaxy S10e'
        self.fields['price'].widget.attrs['placeholder'] = 'eg. 1234.00'
        self.fields['stock'].widget.attrs['placeholder'] = 'eg. 1000'
        self.fields['buy_price'].widget.attrs['placeholder'] = 'eg. 1000.00'
    
    def clean(self):
        cleaned_data = super(ProductForm, self).clean()

class ProductEditForm(forms.ModelForm):
    image = forms.ImageField(required=False, error_messages={'invalid': ("Image files only")},
                                       widget=forms.FileInput)
    description = forms.CharField(required=False, error_messages={"Required": ("This field is Required")}, widget=forms.Textarea())
    class Meta:
        model = Product
        fields = ['product_name', 'price', 'stock','buy_price','image', 'description', 'expire_date','category', 'image']



class ProductVariationForm(forms.ModelForm):
    class Meta:
        model = ProductVariation
        fields = ['product', 'price', 'stock', 'variations']   


class EmailForm(forms.Form):
    email = forms.EmailField(required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)