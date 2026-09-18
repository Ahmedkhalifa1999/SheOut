"""Guards against the broken asset references the review found on every page."""

import re
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from .helpers import add_to_cart, make_product, make_user

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
STATIC_TAG = re.compile(r"""{%\s*static\s+['"]([^'"]+)['"]\s*%}""")
LOCAL_ASSET = re.compile(r"""(?:src|href)=["'](?!https?://|mailto:|tel:|#|{{|{%|/)([^"']+)["']""")


class StaticReferenceTests(TestCase):
    def templates(self):
        return sorted(TEMPLATE_DIR.rglob("*.html"))

    def test_every_static_tag_points_at_an_existing_file(self):
        missing = []
        for template in self.templates():
            for path in STATIC_TAG.findall(template.read_text()):
                if path and finders.find(path) is None:
                    missing.append(f"{template.relative_to(TEMPLATE_DIR)}: {path}")
        self.assertEqual(missing, [])

    def test_no_static_tag_wraps_an_absolute_url(self):
        offenders = [
            f"{t.relative_to(TEMPLATE_DIR)}: {p}"
            for t in self.templates()
            for p in STATIC_TAG.findall(t.read_text())
            if p.startswith(("http://", "https://"))
        ]
        self.assertEqual(offenders, [])

    def test_no_relative_asset_paths(self):
        # Relative `images/...` paths resolve under the current URL and 404.
        offenders = [
            f"{t.relative_to(TEMPLATE_DIR)}: {p}"
            for t in self.templates()
            for p in LOCAL_ASSET.findall(t.read_text())
            if p.startswith(("images/", "css/", "js/"))
        ]
        self.assertEqual(offenders, [])

    def test_stylesheet_imports_exist(self):
        css = Path(finders.find("css/style.css")).read_text()
        for name in re.findall(r"@import url\(([^)'\"]+)\)", css):
            self.assertIsNotNone(finders.find(f"css/{name}"), name)


class PageRenderTests(TestCase):
    """Every page renders with the shared chrome, and template variables are quoted."""

    def setUp(self):
        self.user = make_user()
        self.product = make_product(name="Red shirt", stock=3)

    def assert_page(self, url, *needles):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        html = response.content.decode()
        self.assertIn("images/logo.png", html)
        self.assertIn("bootstrap-4.6.2.bundle.min.js", html)
        self.assertNotRegex(html, r'(?:src|value|href)=(?!["\'])\S')
        for needle in needles:
            self.assertIn(needle, html)
        return html

    def test_public_pages(self):
        self.assert_page(reverse("store:index"), "Featured Products")
        self.assert_page(reverse("store:product_list"), "Red shirt")
        self.assert_page(self.product.get_absolute_url(), "Red shirt")
        self.assert_page(reverse("store:about"))
        self.assert_page(reverse("store:login"))
        self.assert_page(reverse("store:register"))

    def test_authenticated_pages(self):
        self.client.force_login(self.user)
        add_to_cart(self.user, self.product, quantity=1)
        self.assert_page(reverse("store:cart"), "Red shirt")
        self.assert_page(reverse("store:checkout"), "Red shirt")
        self.assert_page(reverse("store:order_list"))
        self.assert_page(self.product.get_absolute_url(), "Add to cart")

    def test_product_name_is_escaped(self):
        product = make_product(name='<script>alert("x")</script>', stock=1)
        html = self.assert_page(product.get_absolute_url())
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)
