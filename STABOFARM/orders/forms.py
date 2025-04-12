from django import forms
from .models import Payment


class PymentForm(forms.ModelForm):
    payment_slip = forms.ImageField(required=False, error_messages={'invalid': ("Image files only")},
                                       widget=forms.FileInput)
    payment_methods = forms.CharField(required=False, error_messages={"Required": ("This field is Required")}, widget=forms.TextInput())
    payment_id = forms.CharField(required=False, error_messages={"Required": ("This field is Required")}, widget=forms.TextInput())

    class Meta:
        model = Payment
        fields = ['payment_slip','payment_methods', 'payment_id']

    def clean(self):
        cleaned_data = super(PymentForm, self).clean()



class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)