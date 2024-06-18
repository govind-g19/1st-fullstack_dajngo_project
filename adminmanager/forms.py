from django import forms
from .models import Variant, Product, ReviewRating, ProductOffers
from .models import CategoryOffers
from orders.models import Orders
from django.core.exceptions import ValidationError


class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        product_id = kwargs.pop('product_id', None)
        super().__init__(*args, **kwargs)
        if product_id:
            product = Product.objects.get(id=product_id)
            self.fields['product'].queryset = Product.objects.filter(id=product_id)
            self.fields['product'].initial = product

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        ram = cleaned_data.get('ram')
        internal_memory = cleaned_data.get('internal_memory')
        final_price = cleaned_data.get('final_price')
        quantity = cleaned_data.get('quantity')
        low_stock_threshold = cleaned_data.get('low_stock_threshold')

        # Check for duplicate variant
        if product and ram and internal_memory:
            existing_variant = Variant.objects.filter(
                product=product,
                ram=ram,
                internal_memory=internal_memory
            )
            if self.instance and self.instance.pk:
                existing_variant = existing_variant.exclude(pk=self.instance.pk)
            if existing_variant.exists():
                raise ValidationError('A variant with the same product, RAM, and internal memory already exists.')

        # Validate final_price
        if final_price is not None and final_price < 0:
            raise ValidationError('Final price cannot be less than zero.')

        # Validate quantity
        if quantity is not None and quantity < 0:
            raise ValidationError('Quantity cannot be less than zero.')

        # Validate low_stock_threshold
        if low_stock_threshold is not None and low_stock_threshold < 0:
            raise ValidationError("Low stock threshold can't be less than zero.")

        if low_stock_threshold is not None and quantity is not None and low_stock_threshold > quantity:
            raise ValidationError(
                'Low stock threshold should be less than or equal to quantity.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
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


class CategoryOfferform(forms.ModelForm):
    class Meta:
        model = CategoryOffers
        fields = '__all__'
        widgets = {
            'category_offer': forms.TextInput(attrs={
                'required': True,
                'class': 'form-control'
            }),
            'discount': forms.NumberInput(attrs={
                'required': True,
                'class': 'form-control'
            }),
            'valid_from': forms.DateInput(attrs={
                'required': True,
                'class': 'form-control',
                'type': 'date'
            }),
            'valid_to': forms.DateInput(attrs={
                'required': True,
                'class': 'form-control',
                'type': 'date'
            }),
            'active': forms.CheckboxInput()
        }

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        discount = cleaned_data.get('discount')
        category_offer = cleaned_data.get('category_offer')

        # Check if valid_from is not later than valid_to
        if valid_from and valid_to:
            if valid_from > valid_to:
                self.add_error('valid_from', 'Valid from date should not be later than valid to date.')

        # Validate discount range (0 to 100)
        if discount is not None:
            if discount < 0 or discount > 100:
                self.add_error('discount', 'Discount should be between 0 and 100.')

        # Validate category_offer contains only alphabetic characters
        if category_offer:
            if not category_offer.isalpha():
                self.add_error('category_offer', 'Category offer name should only contain alphabetic characters.')

        # Check for existing offers with overlapping date ranges and same category_offer
        if valid_from and valid_to and category_offer:
            existing_offer = CategoryOffers.objects.filter(
                valid_from__lte=valid_to,
                valid_to__gte=valid_from,
                category_offer=category_offer
            )
            if self.instance and self.instance.pk:
                existing_offer = existing_offer.exclude(pk=self.instance.pk)
            if existing_offer.exists():
                self.add_error(None, 'A similar offer already exists for this date range and category.')

        return cleaned_data
