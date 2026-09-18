from django.test import TestCase
from django.urls import reverse

from store.models import CartItem

from .helpers import add_to_cart, make_product, make_user


class CartAddTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.product = make_product(name="Red shirt", price="120.00", stock=5)
        self.url = reverse("store:cart_add", args=[self.product.slug])

    def test_add_creates_a_line_and_redirects_to_cart(self):
        response = self.client.post(self.url, {"size": "M", "quantity": 2})
        self.assertRedirects(response, reverse("store:cart"))
        line = CartItem.objects.get(user=self.user)
        self.assertEqual((line.product, line.size, line.quantity), (self.product, "M", 2))

    def test_product_name_with_a_space_works(self):
        # Used to submit "red" because the hidden input value was unquoted.
        response = self.client.post(self.url, {"size": "M", "quantity": 1})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_adding_the_same_size_again_merges_quantities(self):
        self.client.post(self.url, {"size": "M", "quantity": 2})
        self.client.post(self.url, {"size": "M", "quantity": 1})
        self.assertEqual(CartItem.objects.get(user=self.user).quantity, 3)

    def test_different_sizes_stay_separate(self):
        self.client.post(self.url, {"size": "M", "quantity": 1})
        self.client.post(self.url, {"size": "L", "quantity": 1})
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 2)

    def test_invalid_input_is_rejected_without_a_crash(self):
        for payload in (
            {"size": "M", "quantity": "abc"},
            {"size": "M", "quantity": -3},
            {"size": "M", "quantity": 0},
            {"size": "M", "quantity": 21},
            {"size": "GIANT", "quantity": 1},
            {"quantity": 1},
            {},
        ):
            response = self.client.post(self.url, payload)
            self.assertRedirects(response, self.product.get_absolute_url(), msg_prefix=str(payload))
        self.assertEqual(CartItem.objects.count(), 0)

    def test_more_than_stock_is_refused(self):
        response = self.client.post(self.url, {"size": "M", "quantity": 6}, follow=True)
        self.assertContains(response, "Only 5 of Red shirt in stock")
        self.assertEqual(CartItem.objects.count(), 0)

    def test_merge_that_would_exceed_stock_is_refused(self):
        self.client.post(self.url, {"size": "M", "quantity": 4})
        self.client.post(self.url, {"size": "M", "quantity": 4})
        self.assertEqual(CartItem.objects.get(user=self.user).quantity, 4)

    def test_unknown_product_is_a_404(self):
        response = self.client.post(
            reverse("store:cart_add", args=["nope"]), {"size": "M", "quantity": 1}
        )
        self.assertEqual(response.status_code, 404)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()
        response = self.client.post(self.url, {"size": "M", "quantity": 1})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("store:login"), response["Location"])
        self.assertEqual(CartItem.objects.count(), 0)


class CartPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.shirt = make_product(name="Blue shirt", price="80.00")
        self.pants = make_product(name="Black pants", price="200.00")

    def test_empty_cart_message(self):
        response = self.client.get(reverse("store:cart"))
        self.assertContains(response, "Your cart is empty")
        self.assertNotContains(response, "Lorem ipsum")

    def test_rows_show_real_price_size_quantity_and_totals(self):
        add_to_cart(self.user, self.shirt, size="M", quantity=2)
        add_to_cart(self.user, self.pants, size="L", quantity=1)
        response = self.client.get(reverse("store:cart"))
        self.assertContains(response, "Blue shirt")
        self.assertContains(response, "80.00 EGP")
        self.assertContains(response, "160.00 EGP")  # line total
        self.assertContains(response, "360.00 EGP")  # cart total
        self.assertContains(response, 'value="2"')
        self.assertContains(response, "product-placeholder.png")
        self.assertNotContains(response, "Lorem ipsum")
        self.assertNotContains(response, "$ 80.0")

    def test_other_users_lines_are_not_shown(self):
        other = make_user("other@example.com")
        add_to_cart(other, self.shirt, quantity=1)
        response = self.client.get(reverse("store:cart"))
        self.assertContains(response, "Your cart is empty")

    def test_navbar_cart_badge_counts_units(self):
        add_to_cart(self.user, self.shirt, size="M", quantity=2)
        add_to_cart(self.user, self.shirt, size="L", quantity=3)
        response = self.client.get(reverse("store:index"))
        self.assertContains(response, 'id="cart-count">5<')


class CartUpdateRemoveTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.product = make_product(stock=3)
        self.line = add_to_cart(self.user, self.product, quantity=1)

    def test_update_changes_quantity(self):
        response = self.client.post(
            reverse("store:cart_update", args=[self.line.pk]), {"quantity": 3}
        )
        self.assertRedirects(response, reverse("store:cart"))
        self.line.refresh_from_db()
        self.assertEqual(self.line.quantity, 3)

    def test_update_rejects_invalid_and_over_stock(self):
        for quantity in ("abc", 0, -1, 4):
            self.client.post(
                reverse("store:cart_update", args=[self.line.pk]), {"quantity": quantity}
            )
            self.line.refresh_from_db()
            self.assertEqual(self.line.quantity, 1, quantity)

    def test_remove_deletes_the_line(self):
        response = self.client.post(reverse("store:cart_remove", args=[self.line.pk]))
        self.assertRedirects(response, reverse("store:cart"))
        self.assertFalse(CartItem.objects.filter(pk=self.line.pk).exists())

    def test_cannot_touch_another_users_line(self):
        other = make_user("other@example.com")
        other_line = add_to_cart(other, self.product, quantity=1)
        self.assertEqual(
            self.client.post(reverse("store:cart_remove", args=[other_line.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.post(
                reverse("store:cart_update", args=[other_line.pk]), {"quantity": 2}
            ).status_code,
            404,
        )
        other_line.refresh_from_db()
        self.assertEqual(other_line.quantity, 1)

    def test_update_and_remove_require_post(self):
        self.assertEqual(
            self.client.get(reverse("store:cart_update", args=[self.line.pk])).status_code, 405
        )
        self.assertEqual(
            self.client.get(reverse("store:cart_remove", args=[self.line.pk])).status_code, 405
        )
