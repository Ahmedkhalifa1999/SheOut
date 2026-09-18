from django.db.models import Sum

from .models import CartItem, Category


def cart_summary(request):
    """Expose the cart unit count and the category list to every template."""
    context = {"categories": Category.choices, "cart_count": 0}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        count = CartItem.objects.filter(user=user).aggregate(n=Sum("quantity"))["n"] or 0
        context["cart_count"] = count
    return context
