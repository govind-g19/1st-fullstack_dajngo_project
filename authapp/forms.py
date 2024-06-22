from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import validators


class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password', widget=forms.PasswordInput, validators=[
            validators.MinLengthValidator(8),
            validators.RegexValidator(r'^(?=.*[A-Z])', '''Password must
                                      contain at least one uppercase
                                       letter'''),
            validators.RegexValidator(r'^(?=.*[a-z])', '''Password must
                                      contain at least one lowercase
                                      letter'''),
            validators.RegexValidator(r'^(?=.*\d)', '''Password must contain
                                      at least one digit'''),
            validators.RegexValidator(r'^(?=.*[@$!%*?&])', '''Password must
                                      contain at least one special
                                      character''')
        ])
    password2 = forms.CharField(label='Confirm Password',
                                widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match")

        return cleaned_data
