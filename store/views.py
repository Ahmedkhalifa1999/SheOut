from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    AddToCartForm,
    CartUpdateForm,
    CheckoutForm,
    LoginForm,
    RegisterForm,
    ShopFilterForm,
)
from .models import CartItem, Category, EmptyCartError, InsufficientStockError, Order, Product

PRODUCTS_PER_PAGE = 12


# --- Storefront -------------------------------------------------------------


CATEGORY_TILES = [
    (Category.SHIRTS, "images/shirt-img.jpg"),
    (Category.SKIRTS, "images/big-img-01.jpg"),
    (Category.PANTS, "images/big-img-02.jpg"),
    (Category.DRESSES, "images/big-img-03.jpg"),
    (Category.JACKETS, "images/t-shirts-img.jpg"),
]


def index(request):
    featured = Product.objects.filter(stock__gt=0).order_by("-created_at")[:8]
    tiles = [(value, value.label, image) for value, image in CATEGORY_TILES]
    return render(request, "store/index.html", {"featured": featured, "category_tiles": tiles})


def product_list(request):
    form = ShopFilterForm(request.GET or None)
    products = form.apply(Product.objects.all())
    paginator = Paginator(products, PRODUCTS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "store/product_list.html",
        {
            "form": form,
            "page": page,
            "querystring": query.urlencode(),
            "total": paginator.count,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    form = AddToCartForm()
    return render(request, "store/product_detail.html", {"product": product, "form": form})


def about(request):
    return render(request, "store/about.html")


# --- Cart -------------------------------------------------------------------


def _cart_context(user):
    items = list(CartItem.objects.filter(user=user).select_related("product"))
    total = sum((item.line_total for item in items), Decimal("0.00"))
    return {"items": items, "total": total}


@login_required
def cart(request):
    return render(request, "store/cart.html", _cart_context(request.user))


@login_required
@require_POST
def cart_add(request, slug):
    product = get_object_or_404(Product, slug=slug)
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please choose a valid size and quantity.")
        return redirect(product)
    size = form.cleaned_data["size"]
    quantity = form.cleaned_data["quantity"]

    with transaction.atomic():
        line, created = CartItem.objects.select_for_update().get_or_create(
            user=request.user, product=product, size=size, defaults={"quantity": quantity}
        )
        wanted = quantity if created else line.quantity + quantity
        if wanted > product.stock:
            if created:
                line.delete()
            messages.error(
                request,
                f"Only {product.stock} of {product.name} in stock; you asked for {wanted}.",
            )
            return redirect(product)
        if not created:
            line.quantity = wanted
            line.save(update_fields=["quantity"])
    messages.success(request, f"Added {quantity} x {product.name} ({size}) to your cart.")
    return redirect("store:cart")


@login_required
@require_POST
def cart_update(request, pk):
    line = get_object_or_404(CartItem.objects.select_related("product"), pk=pk, user=request.user)
    form = CartUpdateForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Quantity must be a whole number between 1 and 20.")
    elif form.cleaned_data["quantity"] > line.product.stock:
        messages.error(request, f"Only {line.product.stock} of {line.product.name} in stock.")
    else:
        line.quantity = form.cleaned_data["quantity"]
        line.save(update_fields=["quantity"])
        messages.success(request, "Cart updated.")
    return redirect("store:cart")


@login_required
@require_POST
def cart_remove(request, pk):
    line = get_object_or_404(CartItem, pk=pk, user=request.user)
    line.delete()
    messages.success(request, f"Removed {line.product.name} from your cart.")
    return redirect("store:cart")


# --- Checkout and orders ----------------------------------------------------


@login_required
def checkout(request):
    context = _cart_context(request.user)
    if not context["items"]:
        messages.info(request, "Your cart is empty.")
        return redirect("store:product_list")

    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            order = Order.place_from_cart(request.user, form.cleaned_data["address"])
        except EmptyCartError:
            messages.info(request, "Your cart is empty.")
            return redirect("store:product_list")
        except InsufficientStockError as exc:
            messages.error(
                request,
                f"Only {exc.available} of {exc.product.name} in stock; "
                f"your cart asks for {exc.requested}.",
            )
            return redirect("store:cart")
        messages.success(request, f"Order #{order.pk} placed. Thank you!")
        return redirect(order)

    context["form"] = form
    return render(request, "store/checkout.html", context)


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("lines__product")
    return render(request, "store/order_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related("lines__product"), pk=pk, user=request.user
    )
    return render(
        request, "store/order_detail.html", {"order": order, "title": f"Order #{order.pk}"}
    )


# --- Accounts ---------------------------------------------------------------


def register(request):
    if request.user.is_authenticated:
        return redirect("store:index")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error("email", "An account with this email already exists.")
        else:
            login(request, user)
            messages.success(request, "Welcome to SheOut! Your account is ready.")
            return redirect("store:index")
    return render(request, "store/register.html", {"form": form})


class StoreLoginView(LoginView):
    template_name = "store/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class StoreLogoutView(LogoutView):
    http_method_names = ["post", "options"]


def legacy_login_register(request):
    """Old `/login_register/` URL: keep bookmarks working."""
    return redirect("store:login", permanent=True)
