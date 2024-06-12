from django import forms
from authapp.models import Address, Coupons
from django import forms
# from django.utils import timezone
from django.core.validators import MinValueValidator, RegexValidator


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['first_name', 'second_name', 'house_address', 'phone_number', 'city', 'state', 'pin_code', 'land_mark']

    first_name = forms.CharField(
        max_length=30,
        label="First Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'first_name'})
    )

    second_name = forms.CharField(
        max_length=30,
        label="Second Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'second_name'})
    )

    house_address = forms.CharField(
        max_length=100,
        label="House Address",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'house_address'})
    )

    phone_number = forms.CharField(
        label="Phone Number",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'phone_number'})
    )

    city = forms.CharField(
        max_length=50,
        label="City",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'city'})
    )

    state = forms.CharField(
        max_length=50,
        label="State",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'state'})
    )

    pin_code = forms.CharField(
        max_length=10,
        label="Pin Code",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'pin_code'})
    )

    land_mark = forms.CharField(
        max_length=100,
        label="Landmark",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'land_mark'})
    )


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupons
        fields = ['description', 'minimum_amount', 'discount', 'valid_from', 'valid_to']

    description = forms.CharField(
        max_length=100,
        label="Description",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'description'})
    )

    minimum_amount = forms.IntegerField(
        label="Minimum Amount",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'minimum_amount'}),
        validators=[
            MinValueValidator(0, message="Minimum amount must be a positive number"),
            RegexValidator(r'^\d+$', message="Only numeric values are allowed for minimum amount")
        ]
    )

    discount = forms.IntegerField(
        label="Discount",
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'discount'}),
        validators=[
            MinValueValidator(0, message="Discount must be a positive number"),
            RegexValidator(r'^[0-9]+$', message="Discount must contain only numbers")
        ]
    )

    valid_from = forms.DateTimeField(
        label="Valid From",
        widget=forms.DateTimeInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'valid_from'})
    )

    valid_to = forms.DateTimeField(
        label="Valid To",
        widget=forms.DateTimeInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'valid_to'})
    )

    def clean(self):
        cleaned_data = super(CouponForm, self).clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        discount = cleaned_data.get('discount')
        minimum_amount = cleaned_data.get('minimum_amount')

        # Check if the discount is less than or equal to the minimum amount
        if discount is not None and discount >= minimum_amount:
            raise forms.ValidationError("Discount must be greater than the minimum amount")

        # Check if the valid_from date is before the valid_to date
        if valid_from and valid_to:
            if valid_from > valid_to:
                raise forms.ValidationError("Valid from date cannot be after valid to date")

        return cleaned_data
