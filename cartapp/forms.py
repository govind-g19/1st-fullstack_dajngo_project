from django import forms
from authapp.models import Address, Coupons
from adminmanager.models import Category


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
    brand = forms.ModelChoiceField(queryset=Category.objects.all(), empty_label=None, required=False)  # Assuming Category is the model for brand

    class Meta:
        model = Coupons
        fields = ['description', 'minimum_amount', 'discount', 'valid_from', 'valid_to', 'brand']
