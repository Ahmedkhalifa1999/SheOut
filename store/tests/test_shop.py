from django.test import TestCase
from django.urls import reverse

from store.models import Category
from store.views import PRODUCTS_PER_PAGE

from .helpers import make_product


class ProductListTests(TestCase):
    url = reverse("store:product_list")

    def setUp(self):
        self.shirt = make_product(name="Blue shirt", price="80.00", category=Category.SHIRTS)
        self.pants = make_product(name="Black pants", price="200.00", category=Category.PANTS)
        self.dress = make_product(
            name="Red dress", price="500.00", category=Category.DRESSES, stock=0
        )

    def names(self, response):
        return [p.name for p in response.context["page"].object_list]

    def test_lists_everything_by_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.names(response), ["Black pants", "Blue shirt", "Red dress"])
        self.assertContains(response, "Showing 3 of 3 products")
        self.assertContains(response, "Sold out")

    def test_search_filters_by_name(self):
        self.assertEqual(self.names(self.client.get(self.url, {"q": "SHIRT"})), ["Blue shirt"])

    def test_category_filter(self):
        self.assertEqual(
            self.names(self.client.get(self.url, {"category": "Pants"})), ["Black pants"]
        )

    def test_price_range_filter(self):
        response = self.client.get(self.url, {"min_price": 100, "max_price": 300})
        self.assertEqual(self.names(response), ["Black pants"])

    def test_filters_combine(self):
        response = self.client.get(self.url, {"q": "RED", "category": "Dresses", "min_price": 0})
        self.assertEqual(self.names(response), ["Red dress"])

    def test_no_results_message(self):
        response = self.client.get(self.url, {"q": "zzz"})
        self.assertContains(response, "No products match your filters")

    def test_invalid_filters_are_ignored_not_crashed(self):
        response = self.client.get(
            self.url, {"min_price": "abc", "category": "Hats", "max_price": -1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.names(response)), 3)

    def test_inverted_price_range_shows_error(self):
        response = self.client.get(self.url, {"min_price": 500, "max_price": 100})
        self.assertContains(response, "Minimum price cannot be greater")

    def test_pagination(self):
        for i in range(PRODUCTS_PER_PAGE):
            make_product(name=f"Extra {i:02d}")
        first = self.client.get(self.url)
        self.assertEqual(len(first.context["page"].object_list), PRODUCTS_PER_PAGE)
        second = self.client.get(self.url, {"page": 2, "q": ""})
        self.assertEqual(len(second.context["page"].object_list), 3)
        self.assertContains(first, "page=2")


class ProductDetailTests(TestCase):
    def test_detail_page_by_slug(self):
        product = make_product(name="Red shirt", price="120.00", stock=2)
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, "Red shirt")
        self.assertContains(response, "120.00 EGP")
        self.assertContains(response, "Log in to buy")
        self.assertContains(response, 'action="/cart/add/red-shirt/"')

    def test_sold_out_product_has_no_add_form(self):
        product = make_product(stock=0)
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, "Sold out")
        self.assertNotContains(response, "Add to cart")

    def test_unknown_slug_is_404_with_custom_page(self):
        response = self.client.get("/item/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)

    def test_old_query_string_url_is_404_not_500(self):
        self.assertEqual(self.client.get("/item/").status_code, 404)


class IndexTests(TestCase):
    def test_featured_products_are_in_stock_only(self):
        make_product(name="In stock", stock=1)
        make_product(name="Sold out", stock=0)
        response = self.client.get(reverse("store:index"))
        self.assertContains(response, "In stock")
        self.assertNotContains(response, "Sold out")

    def test_category_tiles_link_to_filtered_shop(self):
        response = self.client.get(reverse("store:index"))
        self.assertContains(response, "/shop/?category=Dresses")

    def test_about_page(self):
        self.assertContains(self.client.get(reverse("store:about")), "SheOut STORE")
