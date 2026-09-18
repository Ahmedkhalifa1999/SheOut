from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Category, Order, Size

User = get_user_model()

MAX_LINE_QUANTITY = 20


class RegisterForm(UserCreationForm):
    """Email-as-username registration that runs the configured password validators."""

    email = forms.EmailField(label="Email address", max_length=254)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if (
            User.objects.filter(username__iexact=email).exists()
            or User.objects.filter(email__iexact=email).exists()
        ):
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email address", max_length=254)

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class AddToCartForm(forms.Form):
    size = forms.ChoiceField(choices=Size.choices, initial=Size.M)
    quantity = forms.IntegerField(min_value=1, max_value=MAX_LINE_QUANTITY, initial=1)


class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=MAX_LINE_QUANTITY)


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("address",)
        widgets = {
            "address": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Street, building, city", "class": "form-control"}
            )
        }


class ShopFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=100, label="Search")
    category = forms.ChoiceField(
        required=False, choices=[("", "All categories")] + list(Category.choices)
    )
    min_price = forms.DecimalField(required=False, min_value=Decimal("0"), decimal_places=2)
    max_price = forms.DecimalField(required=False, min_value=Decimal("0"), decimal_places=2)

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_price"), cleaned.get("max_price")
        if low is not None and high is not None and low > high:
            raise forms.ValidationError("Minimum price cannot be greater than maximum price.")
        return cleaned

    def apply(self, queryset):
        """Filter a Product queryset with the cleaned values; invalid forms filter nothing."""
        if not self.is_valid():
            return queryset
        data = self.cleaned_data
        if data.get("q"):
            queryset = queryset.filter(name__icontains=data["q"])
        if data.get("category"):
            queryset = queryset.filter(category=data["category"])
        if data.get("min_price") is not None:
            queryset = queryset.filter(price__gte=data["min_price"])
        if data.get("max_price") is not None:
            queryset = queryset.filter(price__lte=data["max_price"])
        return queryset
