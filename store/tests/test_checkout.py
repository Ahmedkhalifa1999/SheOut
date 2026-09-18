from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from store.models import CartItem, Order

from .helpers import add_to_cart, make_product, make_user


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.product = make_product(name="Blue shirt", price="80.00", stock=5)

    def test_empty_cart_redirects_to_shop_with_message(self):
        response = self.client.get(reverse("store:checkout"), follow=True)
        self.assertRedirects(response, reverse("store:product_list"))
        self.assertContains(response, "Your cart is empty")
        response = self.client.post(reverse("store:checkout"), {"address": "x"})
        self.assertRedirects(response, reverse("store:product_list"))
        self.assertEqual(Order.objects.count(), 0)

    def test_page_shows_real_lines_and_totals(self):
        add_to_cart(self.user, self.product, size="M", quantity=2)
        response = self.client.get(reverse("store:checkout"))
        self.assertContains(response, "Blue shirt")
        self.assertContains(response, "160.00 EGP")
        self.assertNotContains(response, "$ 388")
        self.assertNotContains(response, "Lorem ipsum")

    def test_placing_an_order(self):
        add_to_cart(self.user, self.product, size="M", quantity=2)
        response = self.client.post(
            reverse("store:checkout"), {"address": "1 Test St"}, follow=True
        )
        order = Order.objects.get()
        self.assertRedirects(response, order.get_absolute_url())
        self.assertEqual(order.total, Decimal("160.00"))
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())
        self.assertContains(response, "1 Test St")
        self.assertContains(response, f"Order #{order.pk} placed")

    def test_missing_address_is_rejected(self):
        add_to_cart(self.user, self.product, quantity=1)
        response = self.client.post(reverse("store:checkout"), {"address": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Order.objects.count(), 0)

    def test_long_address_is_stored_in_full(self):
        add_to_cart(self.user, self.product, quantity=1)
        address = "A" * 300
        self.client.post(reverse("store:checkout"), {"address": address})
        self.assertEqual(Order.objects.get().address, address)

    def test_insufficient_stock_shows_error_and_keeps_cart(self):
        add_to_cart(self.user, self.product, quantity=3)
        self.product.stock = 1
        self.product.save()
        response = self.client.post(reverse("store:checkout"), {"address": "x"}, follow=True)
        self.assertRedirects(response, reverse("store:cart"))
        self.assertContains(response, "Only 1 of Blue shirt in stock")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)

    def test_user_without_customer_row_can_check_out(self):
        # There is no separate customer table any more, so any auth user works,
        # including staff created in the admin.
        staff = make_user("staff@example.com", is_staff=True)
        self.client.force_login(staff)
        add_to_cart(staff, self.product, quantity=1)
        response = self.client.post(reverse("store:checkout"), {"address": "HQ"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.get().user, staff)


class OrderPagesTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.product = make_product(price="80.00", stock=5)
        add_to_cart(self.user, self.product, quantity=1)
        self.order = Order.place_from_cart(self.user, "addr")

    def test_order_list_shows_own_orders(self):
        response = self.client.get(reverse("store:order_list"))
        self.assertContains(response, f"#{self.order.pk}")
        self.assertContains(response, "80.00 EGP")

    def test_order_detail_is_private(self):
        other = make_user("other@example.com")
        self.client.force_login(other)
        self.assertEqual(self.client.get(self.order.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(reverse("store:order_list")), f"#{self.order.pk}")

    def test_unknown_order_is_404(self):
        self.assertEqual(
            self.client.get(reverse("store:order_detail", args=[999])).status_code, 404
        )
