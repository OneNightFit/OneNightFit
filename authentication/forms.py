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

class EditProfileForm(forms.ModelForm):
    """Form edit profil. Field yang tampil berbeda untuk Buyer dan Seller."""

    SELLER_ONLY = ("shop_name", "shop_description")
    BUYER_ONLY = ("clothing_size", "chest_cm", "height_cm", "waist_cm", "favorite_styles")

    full_name = forms.CharField(label="Full name", max_length=100)
    favorite_styles = forms.MultipleChoiceField(
        label="Favorite Style",
        choices=Profile.STYLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Profile
        fields = (
            "shop_name", "shop_description", "phone_number", "city",
            "clothing_size", "chest_cm", "height_cm", "waist_cm",
            "favorite_styles",
        )
        labels = {
            "shop_name": "Shop name",
            "shop_description": "Shop description",
            "phone_number": "Phone",
            "city": "City",
            "clothing_size": "Clothing Sizes",
            "chest_cm": "Chest (cm)",
            "height_cm": "Height (cm)",
            "waist_cm": "Waist (cm)",
        }
        widgets = {"shop_description": forms.Textarea(attrs={"rows": 4, "maxlength": 300})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].initial = self.instance.user.first_name
        self.order_fields(["full_name"])
        if self.instance.is_seller:
            self.fields["shop_name"].required = True
            for name in self.BUYER_ONLY:
                del self.fields[name]
        else:
            for name in self.SELLER_ONLY:
                del self.fields[name]
            self.fields["clothing_size"].choices = [("", "Select")] + Profile.SIZE_CHOICES

    def save(self, commit=True):
        profile = super().save(commit=commit)
        if commit:
            user = profile.user
            user.first_name = self.cleaned_data["full_name"].strip()
            user.save(update_fields=["first_name"])
        return profile


class DeleteAccountForm(forms.Form):
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    confirm = forms.BooleanField(
        label="I understand my account and all its data will be permanently deleted."
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password
