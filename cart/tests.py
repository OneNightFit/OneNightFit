"""Simple offline tests for Cart, checkout, and rental availability.

Run with: python manage.py test cart
All products and users are created in Django's temporary test database.
"""
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from authentication.models import Profile
from cart import catalog, reports, services
from cart.models import Cart, CartItem, Rental, local_rental_date
from catalog.models import Product

SUCCESS_MESSAGE = "Your rental is confirmed!"


def make_user(username):
    """Create a local dummy account; no external service is used."""
    User = get_user_model()
    user = User.objects.create_user(
        username=username, first_name=username.title(), password="test-password"
    )
    user.profile.phone_number = "081234567890"
    user.profile.city = "Depok"
    user.profile.save(update_fields=["phone_number", "city"])
    return user


def make_product(name="Dummy item", seller=None, price="25000.000"):
    """Create a dummy Catalog product with a UUID primary key."""
    return Product.objects.create(
        name=name,
        seller=seller,
        description="Test product",
        image="https://example.test/item.jpg",
        price=Decimal(price),
        category="women_clothing",
        size="M",
    )


def make_rental(buyer, product, seller=None, status=Rental.STATUS_PENDING,
                rental_date=None, total=25000, days=1):
    return Rental.objects.create(
        buyer=buyer,
        seller=seller,
        status=status,
        product_uuid=product.pk,
        rental_date=rental_date or local_rental_date(),
        product_name=product.name,
        image=product.image or "",
        store_slug="test-store",
        store_name="Test Store",
        price_per_day=25000,
        days=days,
        total=total,
    )


class CartTestMixin:
    def add_to_cart(self, product, days=1):
        return self.client.post(reverse("cart:add"), {"product_id": product.pk, "days": days})

    def select_product(self, product, selected="on"):
        return self.client.post(reverse("cart:select"), {
            "product_id": product.pk, "selected": selected,
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def checkout_payload(self):
        response = self.client.get(reverse("cart:checkout"))
        payload = {f"shipping_{store['slug']}": "pickup"
                   for store in response.context["summary"]["stores"]}
        payload["payment"] = "qris"
        return payload

    def prepare_checkout(self, product, days=1):
        self.add_to_cart(product, days)
        self.select_product(product)
        return self.checkout_payload()


class CartServiceTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.state = {"items": []}

    def test_add_product_and_calculate_total(self):
        services.add_item(self.state, self.product.pk, 2, selected=True)
        cart = services.build_cart(self.state)
        self.assertEqual(cart["item_count"], 1)
        self.assertEqual(cart["total"], catalog.daily_rent(self.product.price) * 2)

    def test_duplicate_add_does_not_duplicate_product(self):
        services.add_item(self.state, self.product.pk)
        services.add_item(self.state, self.product.pk)
        self.assertEqual(len(self.state["items"]), 1)

    def test_duration_must_be_between_one_and_thirty_days(self):
        services.add_item(self.state, self.product.pk)
        for value in (0, -1, 31, "abc", "1.5"):
            with self.subTest(value=value), self.assertRaises(services.CartError):
                services.set_days(self.state, self.product.pk, value)

    def test_select_and_remove_product(self):
        services.add_item(self.state, self.product.pk, selected=False)
        self.assertEqual(services.build_cart(self.state)["selected_count"], 0)
        services.set_selected(self.state, self.product.pk, "on")
        self.assertEqual(services.build_cart(self.state)["selected_count"], 1)
        services.remove_item(self.state, self.product.pk)
        self.assertEqual(services.build_cart(self.state)["item_count"], 0)

    def test_invalid_or_missing_product_is_rejected(self):
        with self.assertRaises(services.CartError):
            services.add_item(self.state, "not-a-uuid")
        with self.assertRaises(services.CartError):
            services.add_item(self.state, "00000000-0000-0000-0000-000000000001")

    def test_checkout_summary_contains_selected_items_only(self):
        other = make_product(name="Second item")
        services.add_item(self.state, self.product.pk, selected=True)
        services.add_item(self.state, other.pk, selected=False)
        summary = services.checkout_summary(self.state)
        self.assertEqual(summary["selected_count"], 1)
        self.assertEqual(len(summary["stores"]), 1)
        self.assertEqual(len(summary["stores"][0]["items"]), 1)

    def test_checkout_validation_needs_shipping_and_payment(self):
        services.add_item(self.state, self.product.pk, selected=True)
        summary = services.checkout_summary(self.state)
        self.assertTrue(services.validate_checkout(summary, {}, ""))
        store = summary["stores"][0]["slug"]
        self.assertEqual(services.validate_checkout(summary, {store: "pickup"}, "qris"), [])

    def test_checkout_validation_rejects_empty_cart(self):
        summary = services.checkout_summary(self.state)
        self.assertTrue(services.validate_checkout(summary, {}, "qris"))

    def test_complete_checkout_removes_paid_items_only(self):
        other = make_product(name="Second item")
        services.add_item(self.state, self.product.pk, selected=True)
        services.add_item(self.state, other.pk, selected=False)
        services.complete_checkout(self.state, services.checkout_summary(self.state))
        self.assertEqual([item["id"] for item in self.state["items"]], [other.pk])

    def test_invalid_selection_and_missing_cart_item_are_rejected(self):
        services.add_item(self.state, self.product.pk)
        with self.assertRaises(services.CartError):
            services.set_selected(self.state, self.product.pk, "maybe")
        with self.assertRaises(services.CartError):
            services.remove_item(self.state, make_product(name="Not in cart").pk)

    def test_unavailable_item_cannot_be_selected(self):
        buyer = make_user("renter")
        services.add_item(self.state, self.product.pk)
        make_rental(buyer, self.product)
        with self.assertRaises(services.CartError):
            services.set_selected(self.state, self.product.pk, "yes")

    def test_store_selection_selects_and_unselects_products(self):
        products = [self.product]
        products.extend(make_product(name=f"Item {i}") for i in range(10))
        groups = {}
        for product in products:
            store = catalog.get_product(product.pk)["store"]
            groups.setdefault(store, []).append(product)
        same_store = next(items for items in groups.values() if len(items) > 1)
        for product in same_store:
            services.add_item(self.state, product.pk)
        store_slug = catalog.get_product(same_store[0].pk)["store"]
        services.set_store_selected(self.state, store_slug, "on")
        self.assertEqual(services.build_cart(self.state)["selected_count"], len(same_store))
        services.set_store_selected(self.state, store_slug, "off")
        self.assertEqual(services.build_cart(self.state)["selected_count"], 0)
        with self.assertRaises(services.CartError):
            services.set_store_selected(self.state, "missing", "on")

    def test_build_cart_skips_deleted_catalog_product_and_clamps_days(self):
        services.add_item(self.state, self.product.pk, selected=True)
        self.state["items"][0]["days"] = 100
        missing_id = make_product(name="Deleted item").pk
        self.state["items"].append({"id": missing_id, "days": 1, "selected": True})
        Product.objects.filter(pk=missing_id).delete()
        cart = services.build_cart(self.state)
        self.assertEqual(cart["item_count"], 1)
        self.assertEqual(cart["stores"][0]["items"][0]["days"], services.MAX_DAYS)


class CartPageTests(CartTestMixin, TestCase):
    def setUp(self):
        self.buyer = make_user("buyer")
        self.product = make_product()
        self.client.force_login(self.buyer)

    def test_cart_page_loads_and_shows_recommendations(self):
        response = self.client.get(reverse("cart:cart"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["recommendations"]), 1)

    def test_add_duration_select_and_remove_endpoints(self):
        self.assertEqual(self.add_to_cart(self.product).status_code, 302)
        self.client.post(reverse("cart:duration"), {"product_id": self.product.pk, "days": 3})
        response = self.client.get(reverse("cart:cart"))
        self.assertEqual(response.context["cart"]["stores"][0]["items"][0]["days"], 3)
        self.select_product(self.product)
        self.assertEqual(self.client.get(reverse("cart:checkout")).context["summary"]["selected_count"], 1)
        self.client.post(reverse("cart:remove"), {"product_id": self.product.pk})
        self.assertEqual(self.client.get(reverse("cart:cart")).context["cart"]["item_count"], 0)

    def test_seller_cannot_access_cart_or_checkout(self):
        seller = make_user("seller")
        seller.profile.role = Profile.Role.SELLER
        seller.profile.save()
        self.client.force_login(seller)
        self.assertRedirects(self.client.get(reverse("cart:cart")), reverse("catalog:catalog_list"))
        self.assertRedirects(self.client.get(reverse("cart:checkout")), reverse("catalog:catalog_list"))

    def test_guest_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("cart:cart"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_seller_products_are_linked_to_seller(self):
        seller = make_user("product-seller")
        product = make_product(seller=seller)
        self.assertEqual(catalog.get_product(product.pk)["seller_id"], seller.pk)

    def test_ajax_cart_change_returns_json(self):
        response = self.client.post(
            reverse("cart:add"), {"product_id": self.product.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_invalid_change_is_json_error_or_redirect(self):
        ajax = self.client.post(
            reverse("cart:remove"), {"product_id": self.product.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(ajax.status_code, 400)
        normal = self.client.post(reverse("cart:remove"), {"product_id": self.product.pk})
        self.assertRedirects(normal, reverse("cart:cart"), fetch_redirect_response=False)

    def test_store_selection_and_duration_delta_endpoints(self):
        products = [self.product]
        products.extend(make_product(name=f"Store item {i}") for i in range(10))
        groups = {}
        for product in products:
            groups.setdefault(catalog.get_product(product.pk)["store"], []).append(product)
        same_store = next(items for items in groups.values() if len(items) > 1)
        for product in same_store:
            self.add_to_cart(product)
        slug = catalog.get_product(same_store[0].pk)["store"]
        response = self.client.post(
            reverse("cart:select"), {"store": slug, "selected": "on"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.client.post(reverse("cart:select"), {"product_id": self.product.pk, "selected": "off"})
        cart_response = self.client.get(reverse("cart:cart"))
        self.assertTrue(any(store["some_selected"] for store in cart_response.context["cart"]["stores"]))
        self.client.post(reverse("cart:duration"), {"product_id": self.product.pk, "delta": "1"})
        self.assertEqual(CartItem.objects.get(cart__user=self.buyer, product=self.product).days, 2)
        self.assertEqual(self.client.post(reverse("cart:duration"), {
            "product_id": self.product.pk, "delta": "bad",
        }).status_code, 302)
        self.assertEqual(self.client.post(reverse("cart:duration"), {
            "product_id": "00000000-0000-0000-0000-000000000001", "delta": "1",
        }).status_code, 302)

    def test_unavailable_or_invalid_add_and_get_mutation(self):
        make_rental(make_user("holder"), self.product)
        response = self.client.post(
            reverse("cart:add"), {"product_id": self.product.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(reverse("cart:add")).status_code, 405)

    def test_seller_ajax_cart_access_is_forbidden(self):
        seller = make_user("ajax-seller")
        seller.profile.role = Profile.Role.SELLER
        seller.profile.save()
        self.client.force_login(seller)
        response = self.client.post(
            reverse("cart:add"), {"product_id": self.product.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 403)


class CheckoutAndRentalTests(CartTestMixin, TestCase):
    def setUp(self):
        self.buyer = make_user("buyer")
        self.seller = make_user("seller")
        self.seller.profile.role = Profile.Role.SELLER
        self.seller.profile.save()
        self.product = make_product(seller=self.seller)
        self.client.force_login(self.buyer)

    def test_successful_checkout_clears_cart_and_creates_pending_rental(self):
        payload = self.prepare_checkout(self.product, days=2)
        response = self.client.post(reverse("cart:checkout"), payload)
        self.assertRedirects(response, reverse("landing_page"))
        self.assertEqual(CartItem.objects.filter(cart__user=self.buyer).count(), 0)
        rental = Rental.objects.get(buyer=self.buyer, product_uuid=self.product.pk)
        self.assertEqual(rental.status, Rental.STATUS_PENDING)
        self.assertEqual(rental.days, 2)
        self.assertEqual(rental.rental_date, local_rental_date())

    def test_checkout_rejects_invalid_payment_and_keeps_cart(self):
        payload = self.prepare_checkout(self.product)
        payload["payment"] = "invalid"
        response = self.client.post(reverse("cart:checkout"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.filter(cart__user=self.buyer).count(), 1)
        self.assertEqual(Rental.objects.count(), 0)

    def test_checkout_uses_name_phone_and_city_from_user_profile(self):
        self.prepare_checkout(self.product)
        response = self.client.get(reverse("cart:checkout"))
        self.assertEqual(response.context["user_info"], {
            "name": self.buyer.get_full_name(),
            "phone": self.buyer.profile.phone_number,
            "address": self.buyer.profile.city,
        })
        self.assertTrue(response.context["profile_complete"])

    def test_checkout_is_blocked_when_any_profile_detail_is_missing(self):
        payload = self.prepare_checkout(self.product)
        valid_name = self.buyer.first_name
        valid_phone = self.buyer.profile.phone_number
        valid_city = self.buyer.profile.city
        missing_details = [
            ("", valid_phone, valid_city),
            (valid_name, "", valid_city),
            (valid_name, valid_phone, ""),
        ]

        for name, phone, city in missing_details:
            with self.subTest(name=name, phone=phone, city=city):
                self.buyer.first_name = name
                self.buyer.save(update_fields=["first_name"])
                self.buyer.profile.phone_number = phone
                self.buyer.profile.city = city
                self.buyer.profile.save(update_fields=["phone_number", "city"])
                response = self.client.post(reverse("cart:checkout"), payload)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context["profile_complete"])
                self.assertContains(response, "Perbarui profil")
                self.assertContains(response, "id=\"checkout-submit\" disabled")
                self.assertEqual(CartItem.objects.filter(cart__user=self.buyer).count(), 1)
                self.assertEqual(Rental.objects.count(), 0)

    def test_active_rental_hides_product_from_other_buyers(self):
        self.client.post(reverse("cart:checkout"), self.prepare_checkout(self.product))
        self.assertFalse(catalog.get_product(self.product.pk)["available"])
        other_buyer = make_user("other-buyer")
        self.client.force_login(other_buyer)
        response = self.client.post(
            reverse("cart:add"), {"product_id": self.product.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)

    def test_buyer_can_rent_again_after_product_is_returned(self):
        self.client.post(reverse("cart:checkout"), self.prepare_checkout(self.product))
        rental = Rental.objects.get(product_uuid=self.product.pk)
        rental.status = Rental.STATUS_RETURNED
        rental.save(update_fields=["status"])
        self.assertTrue(catalog.get_product(self.product.pk)["available"])
        response = self.add_to_cart(self.product)
        self.assertEqual(response.status_code, 302)

    def test_buyer_can_return_own_approved_rental(self):
        self.client.post(reverse("cart:checkout"), self.prepare_checkout(self.product))
        rental = Rental.objects.get(product_uuid=self.product.pk)
        rental.status = Rental.STATUS_APPROVED
        rental.save(update_fields=["status"])
        response = self.client.post(reverse("cart:return_rental", args=[rental.pk]))
        rental.refresh_from_db()
        self.assertEqual(rental.status, Rental.STATUS_RETURNED)
        self.assertEqual(response.status_code, 302)

    def test_seller_can_approve_and_mark_rental_returned(self):
        self.client.post(reverse("cart:checkout"), self.prepare_checkout(self.product))
        rental = Rental.objects.get(product_uuid=self.product.pk)
        self.client.force_login(self.seller)
        response = self.client.post(reverse("cart:approve_rental", args=[rental.pk]))
        rental.refresh_from_db()
        self.assertEqual(rental.status, Rental.STATUS_APPROVED)
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse("cart:seller_return_rental", args=[rental.pk]))
        rental.refresh_from_db()
        self.assertEqual(rental.status, Rental.STATUS_RETURNED)
        self.assertEqual(response.status_code, 302)

    def test_checkout_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("cart:checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_checkout_conflict_keeps_cart_and_shows_error(self):
        payload = self.prepare_checkout(self.product)
        make_rental(make_user("other-renter"), self.product)
        # Simulate a concurrent rental after the cart availability was read.
        with patch("cart.catalog.unavailable_product_ids", return_value=set()):
            response = self.client.post(reverse("cart:checkout"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["errors"], [
            "A product in this cart was just rented by someone else. Please review your cart."
        ])
        self.assertEqual(CartItem.objects.filter(cart__user=self.buyer).count(), 1)
        self.assertEqual(Rental.objects.filter(product_uuid=self.product.pk).count(), 1)

    def test_return_and_approval_permissions_are_restricted(self):
        rental = make_rental(self.buyer, self.product, self.seller, Rental.STATUS_APPROVED)
        self.assertEqual(self.client.post(reverse("cart:seller_return_rental", args=[rental.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("cart:approve_rental", args=[rental.pk])).status_code, 403)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post(reverse("cart:return_rental", args=[rental.pk])).status_code, 403)

    def test_already_processed_rentals_are_not_changed(self):
        rental = make_rental(self.buyer, self.product, self.seller, Rental.STATUS_RETURNED)
        self.client.post(reverse("cart:return_rental", args=[rental.pk]))
        rental.refresh_from_db()
        self.assertEqual(rental.status, Rental.STATUS_RETURNED)


@override_settings(CART_REQUIRE_LOGIN=True)
class CartLoginSettingTests(CartTestMixin, TestCase):
    def test_ajax_cart_change_requires_login(self):
        product = make_product()
        response = self.client.post(
            reverse("cart:remove"), {"product_id": product.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 401)


class CatalogAdapterTests(TestCase):
    def setUp(self):
        self.product = make_product()

    def test_price_is_rounded_and_clamped(self):
        self.assertEqual(catalog.daily_rent("500.000"), catalog.MIN_DAILY_RENT)
        self.assertEqual(catalog.daily_rent("999999.000"), catalog.MAX_DAILY_RENT)

    def test_product_conversion_and_lookup(self):
        item = catalog.to_product(self.product)
        self.assertEqual(item["id"], self.product.pk)
        self.assertEqual(item["image"], self.product.image)
        self.assertEqual(catalog.get_product(self.product.pk)["name"], self.product.name)
        self.assertIsNone(catalog.get_product("00000000-0000-0000-0000-000000000001"))

    def test_empty_and_missing_product_lists(self):
        self.assertEqual(catalog.get_products([]), {})
        self.assertEqual(catalog.get_products(["00000000-0000-0000-0000-000000000001"]), {})
        self.assertTrue(catalog.has_products())
        self.assertEqual(catalog.default_cart_products(), [catalog.to_product(self.product)])
        self.assertEqual(len(catalog.recommended_products(limit=1)), 1)

    def test_unavailable_products_are_not_returned_as_available(self):
        make_rental(make_user("renter"), self.product)
        self.assertFalse(catalog.has_products())
        self.assertEqual(catalog.default_cart_products(), [])
        self.assertEqual(catalog.recommended_products(), [])


class RentalAndCartModelTests(TestCase):
    def test_cart_item_display_and_rental_date_properties(self):
        buyer = make_user("model-buyer")
        cart = Cart.objects.create(user=buyer)
        product = make_product()
        item = CartItem.objects.create(cart=cart, product=product, days=2)
        self.assertIn("2 hari", str(item))
        self.assertEqual(str(cart), f"Cart {buyer}")

        rental = make_rental(buyer, product, days=2, status=Rental.STATUS_APPROVED)
        self.assertTrue(rental.total_display.startswith("Rp"))
        self.assertEqual(rental.end_date, timezone.localtime(rental.created_at).date() + timedelta(days=2))
        self.assertEqual(rental.is_active, rental.rental_date <= local_rental_date() < rental.rental_date + timedelta(days=2))

    def test_rental_is_inactive_when_pending_or_expired(self):
        buyer = make_user("inactive-buyer")
        product = make_product()
        pending = make_rental(buyer, product, status=Rental.STATUS_PENDING)
        self.assertFalse(pending.is_active)
        pending.status = Rental.STATUS_APPROVED
        pending.rental_date = local_rental_date() - timedelta(days=5)
        self.assertFalse(pending.is_active)


class SellerReportTests(TestCase):
    def setUp(self):
        self.seller = make_user("report-seller")
        self.buyer = make_user("report-buyer")

    def test_empty_report_has_six_zero_bars(self):
        with patch("cart.reports.local_rental_date", return_value=date(2026, 1, 15)):
            report = reports.get_seller_report(self.seller)
        self.assertFalse(report.has_data)
        self.assertEqual(report.products_listed, 0)
        self.assertEqual(len(report.monthly_bars), 6)
        self.assertTrue(all(bar.percent == 0 for bar in report.monthly_bars))
        self.assertEqual(report.monthly_bars[0].label, "Aug")
        self.assertEqual(report.total_earnings_display, "Rp 0")

    def test_report_counts_products_rentals_earnings_and_monthly_bars(self):
        with patch("cart.reports.local_rental_date", return_value=date(2026, 6, 15)):
            product_a = make_product(name="Alpha", seller=self.seller)
            product_b = make_product(name="Beta", seller=self.seller)
            old_product = make_product(name="Old", seller=self.seller)
            pending_product = make_product(name="Pending", seller=self.seller)
            make_rental(self.buyer, pending_product, self.seller, Rental.STATUS_PENDING,
                        date(2026, 6, 14), total=1000)
            make_rental(self.buyer, product_a, self.seller, Rental.STATUS_APPROVED,
                        date(2026, 6, 13), total=2000)
            make_rental(self.buyer, product_b, self.seller, Rental.STATUS_RETURNED,
                        date(2026, 5, 20), total=3000)
            make_rental(self.buyer, old_product, self.seller, Rental.STATUS_RETURNED,
                        date(2025, 1, 1), total=4000)
            report = reports.get_seller_report(self.seller)

        self.assertTrue(report.has_data)
        self.assertEqual(report.products_listed, 4)
        self.assertEqual(report.active_rentals, 1)
        self.assertEqual(report.total_rentals, 3)
        self.assertEqual(report.total_earnings, 9000)
        self.assertEqual(max(bar.percent for bar in report.monthly_bars), 100)
        self.assertEqual(len(report.top_items), 3)
        self.assertEqual(report.top_items[0].name, "Alpha")
        self.assertEqual(report.top_items[0].rentals, 1)
        product_cards = {item.name: item for item in report.products}
        self.assertTrue(product_cards["Alpha"].is_rented)
        self.assertTrue(product_cards["Pending"].is_pending)
        self.assertFalse(product_cards["Beta"].is_rented)
        self.assertEqual(product_cards["Alpha"].daily_price_display, "Rp 25.000")
        self.assertTrue(report.recent_rentals[0].status in ("Pending", "Active", "Returned"))

    def test_report_limits_top_items_and_recent_completed_rentals(self):
        with patch("cart.reports.local_rental_date", return_value=date(2026, 6, 15)):
            products = [make_product(name=f"Item {i}", seller=self.seller) for i in range(7)]
            for product in products:
                make_rental(self.buyer, product, self.seller, Rental.STATUS_RETURNED,
                            date(2026, 6, 10), total=1000)
            pending_product = make_product(name="Pending", seller=self.seller)
            make_rental(self.buyer, pending_product, self.seller, Rental.STATUS_PENDING,
                        date(2026, 6, 15), total=500)
            report = reports.get_seller_report(self.seller)
        self.assertEqual(len(report.top_items), 5)
        self.assertEqual(len(report.recent_rentals), 6)
        self.assertEqual(report.recent_rentals[0].status, "Pending")
        self.assertEqual(report.recent_rentals[1].status, "Returned")
        self.assertEqual(report.recent_rentals[1].amount_display, "Rp 1.000")

    def test_report_value_classes_format_values(self):
        self.assertEqual(reports.format_rupiah(1200), "Rp 1.200")
        self.assertEqual(reports.MonthlyBar("Jan", 1200).amount_display, "Rp 1.200")
        recent = reports.RecentRental(1, "Dress", "Buyer", date(2026, 1, 1), "ACTIVE", 500)
        self.assertEqual(recent.status_slug, "active")
        self.assertEqual(recent.amount_display, "Rp 500")
        self.assertEqual(reports.TopItem("Dress", 2).rentals, 2)
