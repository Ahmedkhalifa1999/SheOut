# Hand-written migration: replaces the name-keyed `item` model with `Product`
# (surrogate key, slug, decimal price, image, stock), replaces the email-keyed
# `customer` model with foreign keys to the auth user, renames the remaining
# models to PascalCase, and tightens the fields the templates depend on.
#
# It carries existing rows across so a database created by 0004 keeps its
# products, orders and order lines. Cart rows whose customer has no matching
# auth user are dropped (carts are transient).

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify

SIZE_CHOICES = [("XS", "XS"), ("S", "S"), ("M", "M"), ("L", "L"), ("XL", "XL"), ("XXL", "XXL")]
CATEGORY_CHOICES = [
    ("Shirts", "Shirts"),
    ("Skirts", "Skirts"),
    ("Pants", "Pants"),
    ("Dresses", "Dresses"),
    ("Jackets", "Jackets"),
]
STATUS_CHOICES = [
    ("pending", "Pending"),
    ("paid", "Paid"),
    ("shipped", "Shipped"),
    ("cancelled", "Cancelled"),
]
VALID_SIZES = {code for code, _ in SIZE_CHOICES}


def copy_items_to_products(apps, schema_editor):
    Item = apps.get_model("store", "item")
    Product = apps.get_model("store", "Product")
    used = set()
    for item in Item.objects.all():
        base = slugify(item.name) or "product"
        slug, counter = base, 2
        while slug in used:
            slug = f"{base}-{counter}"
            counter += 1
        used.add(slug)
        Product.objects.create(
            name=item.name,
            slug=slug,
            category=item.category or "Shirts",
            price=Decimal(item.price or 0),
            stock=0,
        )


def link_products_and_users(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    Product = apps.get_model("store", "Product")
    CartItem = apps.get_model("store", "CartItem")
    OrderLine = apps.get_model("store", "OrderLine")
    Order = apps.get_model("store", "Order")

    products = {p.name: p for p in Product.objects.all()}
    users = {u.username: u for u in User.objects.all()}
    now = django.utils.timezone.now()

    for line in OrderLine.objects.all():
        line.product = products[line.item_id]
        if line.price is None:
            line.price = 0
        if line.quantity < 1:
            line.quantity = 1
        if line.size not in VALID_SIZES:
            line.size = "M"
        line.save()

    for order in Order.objects.all():
        order.user = users.get(order.customer_id) if order.customer_id else None
        if order.time is None:
            order.time = now
        order.save()

    merged = {}
    for cart_item in CartItem.objects.order_by("pk"):
        user = users.get(cart_item.customer_id)
        if user is None:
            cart_item.delete()
            continue
        size = cart_item.size if cart_item.size in VALID_SIZES else "M"
        key = (user.pk, cart_item.item_id, size)
        quantity = max(cart_item.quantity, 1)
        if key in merged:
            keeper = merged[key]
            keeper.quantity += quantity
            keeper.save()
            cart_item.delete()
            continue
        cart_item.user = user
        cart_item.product = products[cart_item.item_id]
        cart_item.size = size
        cart_item.quantity = quantity
        cart_item.save()
        merged[key] = cart_item


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("store", "0004_order_address"),
    ]

    operations = [
        # --- New product table, populated from the old name-keyed table.
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(blank=True, max_length=120, unique=True)),
                ("category", models.CharField(choices=CATEGORY_CHOICES, default="Shirts", max_length=20)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("image", models.ImageField(blank=True, upload_to="products/")),
                ("stock", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.RunPython(copy_items_to_products, migrations.RunPython.noop),
        # --- PascalCase model names.
        migrations.RenameModel(old_name="cart_item", new_name="CartItem"),
        migrations.RenameModel(old_name="orderling", new_name="OrderLine"),
        # --- New foreign keys alongside the old ones, then copy the links over.
        migrations.AddField(
            model_name="cartitem",
            name="product",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.product"),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="user",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="cart_items", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="orderline",
            name="product",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="store.product"),
        ),
        migrations.AddField(
            model_name="order",
            name="user",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(link_products_and_users, migrations.RunPython.noop),
        # --- Drop the old keys and tables.
        migrations.RemoveField(model_name="cartitem", name="item"),
        migrations.RemoveField(model_name="cartitem", name="customer"),
        migrations.RemoveField(model_name="orderline", name="item"),
        migrations.RemoveField(model_name="order", name="customer"),
        migrations.DeleteModel(name="customer"),
        migrations.DeleteModel(name="item"),
        # --- Tighten the fields now that every row is linked.
        migrations.AlterField(
            model_name="cartitem",
            name="product",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to="store.product"),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="user",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cart_items", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="size",
            field=models.CharField(choices=SIZE_CHOICES, max_length=3),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="quantity",
            field=models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="added_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="orderline",
            name="product",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="store.product"),
        ),
        migrations.RenameField(model_name="orderline", old_name="main_order", new_name="order"),
        migrations.AlterField(
            model_name="orderline",
            name="order",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="store.order"),
        ),
        migrations.RenameField(model_name="orderline", old_name="price", new_name="unit_price"),
        migrations.AlterField(
            model_name="orderline",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name="orderline",
            name="size",
            field=models.CharField(choices=SIZE_CHOICES, max_length=3),
        ),
        migrations.AlterField(
            model_name="orderline",
            name="quantity",
            field=models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.RenameField(model_name="order", old_name="time", new_name="created_at"),
        migrations.AlterField(
            model_name="order",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="address",
            field=models.TextField(),
        ),
        migrations.AddField(
            model_name="order",
            name="status",
            field=models.CharField(choices=STATUS_CHOICES, default="pending", max_length=10),
        ),
        # --- Constraints and ordering.
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(fields=("user", "product", "size"), name="unique_cart_line"),
        ),
        migrations.AlterModelOptions(name="cartitem", options={"ordering": ["added_at", "pk"]}),
        migrations.AlterModelOptions(name="order", options={"ordering": ["-created_at", "-pk"]}),
        migrations.AlterModelOptions(name="orderline", options={"ordering": ["pk"]}),
    ]
