from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify


class Size(models.TextChoices):
    XS = "XS", "XS"
    S = "S", "S"
    M = "M", "M"
    L = "L", "L"
    XL = "XL", "XL"
    XXL = "XXL", "XXL"


class Category(models.TextChoices):
    SHIRTS = "Shirts", "Shirts"
    SKIRTS = "Skirts", "Skirts"
    PANTS = "Pants", "Pants"
    DRESSES = "Dresses", "Dresses"
    JACKETS = "Jackets", "Jackets"


class EmptyCartError(Exception):
    """Raised when an order is placed from a cart with no lines."""


class InsufficientStockError(Exception):
    """Raised when a cart asks for more units than the product has in stock."""

    def __init__(self, product, requested, available):
        self.product = product
        self.requested = requested
        self.available = available
        super().__init__(f"Only {available} of {product.name} in stock, {requested} requested")


class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.SHIRTS)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    image = models.ImageField(upload_to="products/", blank=True)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product_detail", args=[self.slug])

    def _unique_slug(self):
        base = slugify(self.name) or "product"
        slug, counter = base, 2
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return static("images/product-placeholder.png")


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="+")
    size = models.CharField(max_length=3, choices=Size.choices)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["added_at", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product", "size"], name="unique_cart_line")
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product} ({self.size}) for {self.user}"

    @property
    def line_total(self):
        return self.product.price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    address = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"Order #{self.pk}"

    def get_absolute_url(self):
        return reverse("store:order_detail", args=[self.pk])

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), Decimal("0.00"))

    @classmethod
    def place_from_cart(cls, user, address):
        """Turn the user's cart into an order, decrement stock, and empty the cart.

        Runs in one transaction so a stock failure on the third line leaves no
        half-written order behind.
        """
        with transaction.atomic():
            cart_items = list(
                CartItem.objects.filter(user=user)
                .select_related("product")
                .select_for_update(of=("self",))
                .order_by("pk")
            )
            if not cart_items:
                raise EmptyCartError("The cart is empty")

            # Lock and re-read the products so two concurrent checkouts cannot
            # both pass the stock check.
            product_ids = {item.product_id for item in cart_items}
            products = {
                p.pk: p for p in Product.objects.select_for_update().filter(pk__in=product_ids)
            }
            requested = {}
            for item in cart_items:
                requested[item.product_id] = requested.get(item.product_id, 0) + item.quantity
            for product_id, quantity in requested.items():
                product = products[product_id]
                if quantity > product.stock:
                    raise InsufficientStockError(product, quantity, product.stock)

            order = cls.objects.create(user=user, address=address)
            OrderLine.objects.bulk_create(
                [
                    OrderLine(
                        order=order,
                        product=item.product,
                        size=item.size,
                        quantity=item.quantity,
                        unit_price=products[item.product_id].price,
                    )
                    for item in cart_items
                ]
            )
            for product_id, quantity in requested.items():
                product = products[product_id]
                product.stock -= quantity
                product.save(update_fields=["stock"])
            CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()
            return order


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="+")
    size = models.CharField(max_length=3, choices=Size.choices)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity} x {self.product} ({self.size})"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
