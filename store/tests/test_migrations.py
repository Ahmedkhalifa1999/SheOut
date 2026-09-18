"""Exercise the 0005 data migration against rows shaped like the old schema."""

from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

OLD = [("store", "0004_order_address")]
NEW = [("store", "0005_product_user_fk_and_cleanup")]


class ProductAndUserMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        executor.loader.build_graph()
        # Include auth's leaf node so the historical apps registry knows the user model.
        nodes = list(targets) + executor.loader.graph.leaf_nodes("auth")
        return executor.loader.project_state(nodes).apps

    def tearDown(self):
        self.migrate(NEW)

    def test_rows_are_carried_over(self):
        apps = self.migrate(OLD)
        User = apps.get_model("auth", "User")
        Item = apps.get_model("store", "item")
        Customer = apps.get_model("store", "customer")
        CartItem = apps.get_model("store", "cart_item")
        Order = apps.get_model("store", "order")
        OrderLine = apps.get_model("store", "orderling")

        user = User.objects.create(username="first@shop.com", email="first@shop.com")
        User.objects.create(username="ahmed")
        customer = Customer.objects.create(email="first@shop.com")
        orphan = Customer.objects.create(email="orphan@shop.com")
        shirt = Item.objects.create(name="blue shirt", price=80, category=None)
        Item.objects.create(name="blue shirt!", price=90, category="Shirts")
        order = Order.objects.create(customer=customer, time=None, address="any place")
        OrderLine.objects.create(main_order=order, item=shirt, size="4", quantity=0, price=None)
        # duplicate cart rows that must merge, plus one for a customer without a user
        CartItem.objects.create(customer=customer, item=shirt, size="M", quantity=2)
        CartItem.objects.create(customer=customer, item=shirt, size="M", quantity=0)
        CartItem.objects.create(customer=customer, item=shirt, size=None, quantity=1)
        CartItem.objects.create(customer=orphan, item=shirt, size="L", quantity=1)

        apps = self.migrate(NEW)
        Product = apps.get_model("store", "Product")
        CartItem = apps.get_model("store", "CartItem")
        Order = apps.get_model("store", "Order")

        products = {p.name: p for p in Product.objects.all()}
        self.assertEqual(set(products), {"blue shirt", "blue shirt!"})
        self.assertEqual(products["blue shirt"].slug, "blue-shirt")
        self.assertEqual(products["blue shirt!"].slug, "blue-shirt-2")
        self.assertEqual(products["blue shirt"].price, Decimal("80"))
        self.assertEqual(products["blue shirt"].category, "Shirts")

        migrated_order = Order.objects.get()
        self.assertEqual(migrated_order.user_id, user.pk)
        self.assertIsNotNone(migrated_order.created_at)
        self.assertEqual(migrated_order.status, "pending")
        line = migrated_order.lines.get()
        self.assertEqual(line.product_id, products["blue shirt"].pk)
        self.assertEqual((line.size, line.quantity, line.unit_price), ("M", 1, Decimal("0")))

        # (M, 2) + (M, 0 raised to 1) + (null size mapped to M, 1) merge into one line of 4;
        # the orphan customer's row is dropped.
        cart = list(CartItem.objects.order_by("size"))
        self.assertEqual([(c.size, c.quantity, c.user_id) for c in cart], [("M", 4, user.pk)])
