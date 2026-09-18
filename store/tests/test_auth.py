from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .helpers import PASSWORD, make_user

User = get_user_model()


class RegisterTests(TestCase):
    url = reverse("store:register")

    def test_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create new account")

    def test_valid_registration_logs_the_user_in(self):
        response = self.client.post(
            self.url,
            {"email": "New@Example.com", "password1": PASSWORD, "password2": PASSWORD},
        )
        self.assertRedirects(response, reverse("store:index"))
        user = User.objects.get(username="new@example.com")
        self.assertEqual(user.email, "new@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            self.url, {"email": "weak@example.com", "password1": "x", "password2": "x"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This password is too short")
        self.assertFalse(User.objects.filter(username="weak@example.com").exists())

    def test_invalid_email_is_rejected(self):
        response = self.client.post(
            self.url, {"email": "not-an-email", "password1": PASSWORD, "password2": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address")
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email_shows_error_and_creates_nothing(self):
        make_user("taken@example.com")
        response = self.client.post(
            self.url, {"email": "TAKEN@example.com", "password1": PASSWORD, "password2": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(User.objects.count(), 1)

    def test_username_that_is_not_an_email_cannot_be_hijacked(self):
        # A user created in the admin with a plain username used to crash registration
        # with an IntegrityError once someone typed that name into the email box.
        make_user("ahmed")
        response = self.client.post(
            self.url, {"email": "ahmed", "password1": PASSWORD, "password2": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(
            self.url, {"email": "a@example.com", "password1": PASSWORD, "password2": "other"}
        )
        self.assertContains(response, "didn’t match", status_code=200)

    def test_missing_fields_do_not_crash(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_is_redirected_away(self):
        self.client.force_login(make_user())
        self.assertRedirects(self.client.get(self.url), reverse("store:index"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = make_user("shopper@example.com")

    def test_login_page_renders(self):
        self.assertContains(self.client.get(reverse("store:login")), "Account login")

    def test_valid_login_redirects_home(self):
        response = self.client.post(
            reverse("store:login"), {"username": "Shopper@Example.com", "password": PASSWORD}
        )
        self.assertRedirects(response, reverse("store:index"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_honours_next(self):
        response = self.client.post(
            reverse("store:login") + "?next=/cart/",
            {"username": "shopper@example.com", "password": PASSWORD},
        )
        self.assertRedirects(response, "/cart/")

    def test_wrong_password_shows_an_error(self):
        response = self.client.post(
            reverse("store:login"), {"username": "shopper@example.com", "password": "nope"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_missing_fields_do_not_crash(self):
        self.assertEqual(self.client.post(reverse("store:login"), {}).status_code, 200)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("store:logout")).status_code, 405)
        response = self.client.post(reverse("store:logout"))
        self.assertRedirects(response, reverse("store:index"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_legacy_login_register_url_redirects(self):
        response = self.client.get("/login_register/")
        self.assertRedirects(response, reverse("store:login"), status_code=301)


class LoginRequiredTests(TestCase):
    def test_cart_checkout_and_orders_require_login(self):
        for name in ("store:cart", "store:checkout", "store:order_list"):
            url = reverse(name)
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('store:login')}?next={url}", msg_prefix=name)

    def test_browsing_does_not_require_login(self):
        for name in ("store:index", "store:product_list", "store:about"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
