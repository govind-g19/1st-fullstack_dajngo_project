from django import forms
from .models import Variant, Product, ReviewRating, ProductOffers
from orders.models import Orders
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


class UpdateOrderStatusForm(forms.ModelForm):
    STATUS_CHOICES = (
        ('Ordered', 'Ordered'),
        ('Packed', 'Packed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
    )
    status = forms.ChoiceField(choices=STATUS_CHOICES)

    class Meta:
        model = Orders
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select rounded-2',
                                          'style': 'width: 250px; height: 90px;'})
        }


class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = ProductOffers
        fields = '__all__'
        widgets = {
            'product_offer': forms.TextInput(attrs={
                'required': True, 'class': 'form-control'}),
            'valid_from': forms.DateInput(attrs={
                'required': True, 'type': 'date', 'class': 'form-control'}),
            'valid_to': forms.DateInput(attrs={
                'required': True, 'type': 'date', 'class': 'form-control'}),
            'discount': forms.NumberInput(attrs={
                'required': True, 'class': 'form-control'}),
            'active': forms.CheckboxInput()
        }

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        discount = cleaned_data.get('discount')

        # Validate date range
        if valid_from and valid_to:
            if valid_from > valid_to:
                self.add_error('valid_to', "Valid from date cannot be after valid to date")

        # Validate discount range
        if discount is not None:
            if discount < 0 or discount > 100:
                self.add_error('discount', "Discount must be between 0 and 100")

        # Check for existing similar offer
        existing_offer = ProductOffers.objects.filter(
            valid_from__lte=valid_to,
            valid_to__gte=valid_from,
            product_offer=cleaned_data.get('product_offer'),
        )
        if self.instance:
            existing_offer = existing_offer.exclude(pk=self.instance.pk)
        if existing_offer.exists():
            self.add_error(None, "A similar offer already exists")

        return cleaned_data
