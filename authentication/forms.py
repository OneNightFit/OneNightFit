from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import Profile


class SignUpForm(forms.Form):
    role = forms.ChoiceField(
        choices=Profile.Role.choices, initial=Profile.Role.BUYER, widget=forms.RadioSelect
    )
    full_name = forms.CharField(label="Full name", max_length=100)
    shop_name = forms.CharField(label="Shop name", max_length=100, required=False)
    email = forms.EmailField(label="Email", max_length=150)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(username__iexact=email).exists() or \
           User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered. Try logging in instead.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == Profile.Role.SELLER and not cleaned.get("shop_name", "").strip():
            self.add_error("shop_name", "Shop name is required for sellers.")
        password = cleaned.get("password")
        if password:
            try:
                password_validation.validate_password(password)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return cleaned

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password"],
            first_name=data["full_name"].strip(),
        )
        profile = user.profile  # dibuat oleh signal
        profile.role = data["role"]
        if profile.is_seller:
            profile.shop_name = data["shop_name"].strip()
        profile.save()
        return user


class LoginForm(AuthenticationForm):
    """Login memakai email (disimpan sebagai username)."""

    username = forms.EmailField(label="Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    error_messages = {
        "invalid_login": "Incorrect email or password. Check them and try again.",
        "inactive": "This account is inactive.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].lower()
