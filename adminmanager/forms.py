from django import forms
from .models import Variant, Product, ReviewRating
from django.core.exceptions import ValidationError


class VariantForm(forms.ModelForm):
    product = forms.ModelMultipleChoiceField(queryset=Product.objects.all())

    class Meta:
        model = Variant
        fields = ['product', 'ram', 'internal_memory', 'final_price', 'is_available', 'quantity', 'low_stock_threshold', 'deleted']

    def clean(self):
        cleaned_data = super().clean()
        final_price = cleaned_data.get('final_price')
        quantity = cleaned_data.get('quantity')
        low_stock_threshold = cleaned_data.get('low_stock_threshold')

        if final_price is not None and final_price <= 0:
            raise ValidationError('Final price cannot be below zero.')

        if quantity is not None and quantity <= 0:
            raise ValidationError('Quantity cannot be below zero.')
        
        if low_stock_threshold is not None and low_stock_threshold <0:
            raise ValidationError("Low stock threshold can't be less than 0 ")

        if low_stock_threshold is not None and quantity is not None and low_stock_threshold >= quantity:
            raise ValidationError('Low stock threshold should be less than quantity.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        products = self.cleaned_data['product']
        if commit:
            instance.save()
            instance.product.set(products)
        return instance


class ReviewRatingForm(forms.ModelForm):

    class Meta:
        model = ReviewRating
        fields = ("comment", "rating", "review")
        widgets = {
            'comment': forms.TextInput(attrs={'class': 'form-control'}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'review': forms.Textarea(attrs={'class': 'form-control',
                                            'rows': 5}),
        }
