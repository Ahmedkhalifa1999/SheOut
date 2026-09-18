from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from store.models import (
    CartItem,
    EmptyCartError,
    InsufficientStockError,
    Order,
    OrderLine,
)

from .helpers import add_to_cart, make_product, make_user


class ProductTests(TestCase):
    def test_slug_is_generated_and_unique(self):
        first = make_product(name="Red Shirt")
        second = make_product(name="Red Shirt")
        self.assertEqual(first.slug, "red-shirt")
        self.assertEqual(second.slug, "red-shirt-2")

    def test_names_with_spaces_and_punctuation_get_url_safe_slugs(self):
        product = make_product(name="Été / Summer dress!")
        self.assertEqual(product.slug, "ete-summer-dress")
        self.assertEqual(product.get_absolute_url(), "/item/ete-summer-dress/")

    def test_image_url_falls_back_to_placeholder(self):
        product = make_product()
        self.assertTrue(product.image_url.endswith("images/product-placeholder.png"))

    def test_str_and_in_stock(self):
        product = make_product(name="Coat", stock=0)
        self.assertEqual(str(product), "Coat")
        self.assertFalse(product.in_stock)


class CartItemTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(price="12.50")

    def test_line_total_uses_decimal_price(self):
        line = add_to_cart(self.user, self.product, quantity=3)
        self.assertEqual(line.line_total, Decimal("37.50"))

    def test_same_product_and_size_cannot_be_duplicated(self):
        add_to_cart(self.user, self.product, size="M")
        with self.assertRaises(IntegrityError):
            add_to_cart(self.user, self.product, size="M")

    def test_different_sizes_are_separate_lines(self):
        add_to_cart(self.user, self.product, size="M")
        add_to_cart(self.user, self.product, size="L")
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 2)


class PlaceOrderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.shirt = make_product(name="Shirt", price="80.00", stock=5)
        self.pants = make_product(name="Pants", price="200.00", stock=2)

    def test_order_is_created_with_lines_stock_decremented_and_cart_emptied(self):
        add_to_cart(self.user, self.shirt, size="M", quantity=2)
        add_to_cart(self.user, self.pants, size="L", quantity=1)

        order = Order.place_from_cart(self.user, "1 Test St")

        self.assertEqual(order.user, self.user)
        self.assertEqual(order.address, "1 Test St")
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertIsNotNone(order.created_at)
        self.assertEqual(order.lines.count(), 2)
        self.assertEqual(order.total, Decimal("360.00"))
        line = order.lines.get(product=self.shirt)
        self.assertEqual((line.size, line.quantity, line.unit_price), ("M", 2, Decimal("80.00")))
        self.shirt.refresh_from_db()
        self.pants.refresh_from_db()
        self.assertEqual((self.shirt.stock, self.pants.stock), (3, 1))
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_unit_price_is_frozen_at_order_time(self):
        add_to_cart(self.user, self.shirt, quantity=1)
        order = Order.place_from_cart(self.user, "addr")
        self.shirt.price = Decimal("999.00")
        self.shirt.save()
        self.assertEqual(order.total, Decimal("80.00"))

    def test_empty_cart_is_refused(self):
        with self.assertRaises(EmptyCartError):
            Order.place_from_cart(self.user, "addr")
        self.assertEqual(Order.objects.count(), 0)

    def test_insufficient_stock_rolls_back_everything(self):
        add_to_cart(self.user, self.shirt, size="M", quantity=1)
        add_to_cart(self.user, self.pants, size="L", quantity=3)  # only 2 in stock

        with self.assertRaises(InsufficientStockError) as ctx:
            Order.place_from_cart(self.user, "addr")

        self.assertEqual(ctx.exception.product, self.pants)
        self.assertEqual((ctx.exception.requested, ctx.exception.available), (3, 2))
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderLine.objects.count(), 0)
        self.shirt.refresh_from_db()
        self.assertEqual(self.shirt.stock, 5)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 2)

    def test_stock_is_checked_across_sizes_of_the_same_product(self):
        add_to_cart(self.user, self.pants, size="M", quantity=1)
        add_to_cart(self.user, self.pants, size="L", quantity=2)  # 3 total, 2 in stock
        with self.assertRaises(InsufficientStockError):
            Order.place_from_cart(self.user, "addr")

    def test_product_referenced_by_an_order_cannot_be_deleted(self):
        add_to_cart(self.user, self.shirt, quantity=1)
        Order.place_from_cart(self.user, "addr")
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.shirt.delete()

    def test_deleting_user_keeps_order_history(self):
        add_to_cart(self.user, self.shirt, quantity=1)
        order = Order.place_from_cart(self.user, "addr")
        self.user.delete()
        order.refresh_from_db()
        self.assertIsNone(order.user)
        self.assertEqual(order.lines.count(), 1)

    def test_order_str_and_url(self):
        add_to_cart(self.user, self.shirt, quantity=1)
        order = Order.place_from_cart(self.user, "addr")
        self.assertEqual(str(order), f"Order #{order.pk}")
        self.assertEqual(order.get_absolute_url(), f"/orders/{order.pk}/")


class ProductAdminTests(TestCase):
    def test_admin_lists_products_orders_and_cart_items(self):
        admin = make_user("admin@example.com", is_staff=True, is_superuser=True)
        self.client.force_login(admin)
        for url in ("/admin/store/product/", "/admin/store/order/", "/admin/store/cartitem/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
