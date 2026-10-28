"""
Test Cart & Checkout.
Run with: python manage.py test cart

Uses custom Post data without an internet connection or the import_products feature.
USD amounts are converted to IDR by multiplying them by 500.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.test import Client, TestCase
from django.urls import reverse

from authentication.models import create_profile
from cart import catalog, services
from cart.models import Cart, CartItem
from inspo.models import Post, Tag

USD = [50, 30, 60, 20, 40, 40, 40, 40, 40]  # external_id 1..9

def make_posts():
    SUCCESS_MESSAGE = "Your rental is confirmed!"
    LOGIN_HINT = "Login first"


    def make_user(email):
        """Buat akun TANPA memicu sinyal pembuatan Profile milik modul Autentikasi.

        Tes cart hanya butuh akun yang bisa login; tidak perlu bergantung pada model
        Profile (itu tanggung jawab tes modul Autentikasi)."""
        post_save.disconnect(create_profile, sender=settings.AUTH_USER_MODEL)
        try:
            return get_user_model().objects.create_user(email, email=email, password="pw12345")
        finally:
            post_save.connect(create_profile, sender=settings.AUTH_USER_MODEL)


    def cart_ids(response):
        """id produk yang ada di KERANJANG. Sengaja bukan assertNotContains pada seluruh
        halaman: produk yang sudah dibayar boleh muncul lagi di bagian Recommendation."""
        return {i["id"] for g in response.context["cart"]["stores"] for i in g["items"]}
    
    tag, _ = Tag.objects.get_or_create(name="men's clothing")
    return [
        Post.objects.create(
            title=f"Item-{i:02d}", caption="x", image_url=f"https://example.com/{i}.jpg",
            external_id=i, price=Decimal(str(usd)), tag=tag,
        )
        for i, usd in enumerate(USD, start=1)
    ]

class CatalogTests(TestCase):
    def setUp(self):
        self.posts = make_posts()

    def test_price_comes_from_api_price(self):
        self.assertEqual(catalog.get_product(self.posts[0].pk)["price"], 25000)
        self.assertEqual(catalog.get_product(self.posts[2].pk)["price"], 30000)

    def test_price_limits(self):
        low = Post.objects.create(title="Murah", external_id=100, price=Decimal("0.50"))
        high = Post.objects.create(title="Mahal", external_id=101, price=Decimal("999.99"))
        self.assertEqual(catalog.get_product(low.pk)["price"], catalog.MIN_DAILY_RENT)
        self.assertEqual(catalog.get_product(high.pk)["price"], catalog.MAX_DAILY_RENT)

    def test_generated_fields_are_stable(self):
        pk = self.posts[0].pk
        self.assertEqual(catalog.get_product(pk), catalog.get_product(pk))
        p = catalog.get_product(pk)
        self.assertIn(p["store"], catalog.STORES)
        self.assertIn(p["size"], catalog.SIZES)
        self.assertTrue(4.0 <= p["rating"] <= 5.0)

    def test_user_uploaded_posts_are_not_products(self):
        user = get_user_model().objects.create_user("u", password="pw12345")
        mine = Post.objects.create(author=user, title="Upload user")    # tanpa external_id/price
        self.assertIsNone(catalog.get_product(mine.pk))

    def test_recommendations_exclude_cart_items(self):
        recs = catalog.recommended_products(exclude_ids=[p.pk for p in self.posts[:4]], limit=5)
        self.assertEqual(len(recs), 5)
        self.assertFalse({r["id"] for r in recs} & {p.pk for p in self.posts[:4]})

class ServiceTests(TestCase):
    def setUp(self):
        self.posts = make_posts()
        self.state = services.default_state()

    def test_default_cart_matches_design(self):
        cart = services.build_cart(self.state)
        self.assertEqual(cart["total"], 55000)
        self.assertEqual(cart["selected_count"], 2)
        self.assertEqual(cart["item_count"], 4)

    def test_rupiah(self):
        self.assertEqual(services.format_rupiah(55000), "Rp55.000")
        self.assertEqual(services.format_rupiah(0), "Rp0")

    def test_duration_updates_total_and_validates(self):
        services.set_days(self.state, self.posts[0].pk, 3)
        self.assertEqual(services.build_cart(self.state)["total"], 75000 + 30000)
        for bad in (0, -1, "abc", "", None, 31, "1.5"):
            with self.assertRaises(services.CartError):
                services.set_days(self.state, self.posts[0].pk, bad)

    def test_store_selection(self):
        first = catalog.get_product(self.posts[0].pk)["store"]
        services.set_store_selected(self.state, first, "")
        for g in services.build_cart(self.state)["stores"]:
            if g["slug"] == first:
                self.assertFalse(any(i["selected"] for i in g["items"]))
        with self.assertRaises(services.CartError):
            services.set_store_selected(self.state, "toko-tidak-ada", "on")

    def test_remove_and_unknown_ids(self):
        services.remove_item(self.state, self.posts[2].pk)
        self.assertEqual(services.build_cart(self.state)["item_count"], 3)
        for bad in ("x", None, -1, 0, 99999):
            with self.assertRaises(services.CartError):
                services.set_days(self.state, bad, 2)

    def test_tampered_state_is_clamped_and_unknown_dropped(self):
        state = {"items": [{"id": self.posts[0].pk, "days": 999, "selected": True},
                           {"id": 123456, "days": 1, "selected": True}]}
        cart = services.build_cart(state)
        self.assertEqual(cart["item_count"], 1)
        self.assertEqual(cart["total"], 25000 * services.MAX_DAYS)

    def test_complete_checkout_removes_only_paid_items(self):
        summary = services.checkout_summary(self.state)
        services.complete_checkout(self.state, summary)
        self.assertEqual([i["id"] for i in self.state["items"]],
                         [self.posts[2].pk, self.posts[3].pk])

class JsonPostMixin:
    def post_json(self, name, data):
        return self.client.post(reverse(name), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def valid_checkout_payload(self, payment="qris"):
        r = self.client.get(reverse("cart:checkout"))
        payload = {f"shipping_{g['slug']}": "pickup" for g in r.context["summary"]["stores"]}
        payload["payment"] = payment
        return payload

class GuestCartTests(JsonPostMixin, TestCase):
    def setUp(self):
        self.posts = make_posts()

    def test_cart_page_renders(self):
        self.assertEqual(self.client.get(reverse("cart:cart")).status_code, 200)

    def test_cart_shows_products_and_total(self):
        r = self.client.get(reverse("cart:cart"))
        self.assertContains(r, "Item-01")
        self.assertContains(r, "Rp55.000")
        self.assertContains(r, "RECOMMENDATION")

    def test_recommendations_are_five_and_not_in_cart(self):
        r = self.client.get(reverse("cart:cart"))
        recs = {p["id"] for p in r.context["recommendations"]}
        self.assertEqual(len(recs), 5)
        self.assertFalse(recs & {p.pk for p in self.posts[:4]})

    def test_guest_cart_comes_back_on_every_refresh(self):
        self.post_json("cart:remove", {"product_id": self.posts[0].pk})
        self.post_json("cart:duration", {"product_id": self.posts[1].pk, "days": 7})
        r = self.client.get(reverse("cart:cart"))            # refresh
        self.assertContains(r, "Item-01")
        self.assertContains(r, "Rp55.000")

    def test_state_changing_endpoints_reject_get(self):
        for name in ("select", "duration", "remove", "add", "reset"):
            self.assertEqual(self.client.get(reverse(f"cart:{name}")).status_code, 405)

    def test_invalid_input_is_rejected(self):
        pk = self.posts[0].pk
        self.assertEqual(self.post_json("cart:duration", {"product_id": "abc", "days": 2}).status_code, 400)
        self.assertEqual(self.post_json("cart:duration", {"product_id": pk, "days": "-5"}).status_code, 400)
        self.assertEqual(self.post_json("cart:duration", {"product_id": pk, "delta": "-1"}).status_code, 400)
        self.assertEqual(self.post_json("cart:remove", {"product_id": 99999}).status_code, 400)
        self.assertEqual(self.post_json("cart:select", {"store": "nope", "selected": "on"}).status_code, 400)

    def test_browser_cannot_inject_price(self):
        r = self.post_json("cart:duration", {"product_id": self.posts[0].pk, "days": 2, "price": 1, "total": 1})
        self.assertEqual(r.json()["cart"]["total"], 50000 + 30000)

    def test_empty_catalog_shows_hint(self):
        Post.objects.all().delete()
        self.assertContains(self.client.get(reverse("cart:cart")), "import_products")

class AccountCartTests(JsonPostMixin, TestCase):
    def setUp(self):
        self.posts = make_posts()
        User = get_user_model()
        self.alice = User.objects.create_user("alice", password="pw12345")
        self.bob = User.objects.create_user("bob", password="pw12345")

    def test_account_cart_is_seeded_once_and_persists(self):
        self.client.force_login(self.alice)
        self.post_json("cart:duration", {"product_id": self.posts[0].pk, "days": 3})
        r = self.client.get(reverse("cart:cart"))   # Reaload tidak mereset
        self.assertContains(r, "Rp105.000")
        self.assertEqual(CartItem.objects.filter(cart__user=self.alice).count(), 4)

    def test_emptied_cart_is_not_reseeded(self):
        self.client.force_login(self.alice)
        for p in self.posts[:4]:
            self.post_json("cart:remove", {"product_id": p.pk})
        r = self.client.get(reverse("cart:cart"))
        self.assertContains(r, "Your cart is empty")
        self.assertEqual(CartItem.objects.filter(cart__user=self.alice).count(), 0)

    def test_reset_helper_restores_demo_items(self):
        self.client.force_login(self.alice)
        for p in self.posts[:4]:
            self.post_json("cart:remove", {"product_id": p.pk})
        self.client.post(reverse("cart:reset"))
        self.assertEqual(CartItem.objects.filter(cart__user=self.alice).count(), 4)

    def test_one_cart_per_user(self):
        before = Cart.objects.count()
        self.client.force_login(self.alice)
        self.client.get(reverse("cart:cart"))
        self.client.get(reverse("cart:cart"))
        self.assertEqual(Cart.objects.count(), before + 1)

@override_settings(CART_REQUIRE_LOGIN=True, LOGIN_URL="/login/")
class CartLoginRequiredTests(JsonPostMixin, TestCase):
    def setUp(self):
        self.posts = make_posts()

    def test_guest_is_redirected_to_login(self):
        r = self.client.get(reverse("cart:cart"))
        self.assertRedirects(r, "/login/?next=/cart/", fetch_redirect_response=False)

    def test_ajax_gets_401(self):
        self.assertEqual(self.post_json("cart:remove", {"product_id": self.posts[0].pk}).status_code, 401)

    def test_logged_in_user_can_open_cart(self):
        user = get_user_model().objects.create_user("john", password="pw12345")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("cart:cart")).status_code, 200)

class GuestCheckoutTests(JsonPostMixin, TestCase):
    def setUp(self):
        self.posts = make_posts()

    def test_checkout_page_renders(self):
        self.assertEqual(self.client.get(reverse("cart:checkout")).status_code, 200)

    def test_guest_selection_reaches_checkout(self):
        self.post_json("cart:duration", {"product_id": self.posts[0].pk, "days": 3})
        r = self.client.get(reverse("cart:checkout"))
        self.assertContains(r, "Rp105.000") # 25k x 3 + 15k x 2
        self.assertContains(r, "Item-01")
        self.assertContains(r, "Item-02")
        self.assertNotContains(r, "Item-03")  #tidak terpilih

    def test_checkout_with_nothing_selected(self):
        for p in self.posts[:2]:
            self.post_json("cart:select", {"product_id": p.pk}) # kotak tidak dipilih
        self.assertContains(self.client.get(reverse("cart:checkout")), "No products selected")

    def test_guest_success_message_items_gone_then_back_on_refresh(self):
        r = self.client.post(reverse("cart:checkout"), self.valid_checkout_payload(), follow=True)
        self.assertContains(r, "Your rental is confirmed!")
        self.assertNotContains(r, "Item-01")   
        again = self.client.get(reverse("cart:cart"))
        self.assertContains(again, "Item-01")

    def test_checkout_requires_valid_payment_and_shipping(self):
        payload = self.valid_checkout_payload()
        no_pay = {k: v for k, v in payload.items() if k != "payment"}
        r = self.client.post(reverse("cart:checkout"), no_pay)
        self.assertContains(r, "PAYMENT METHODS")
        self.assertNotContains(r, "Your rental is confirmed!")
        bad_ship = {**payload, next(k for k in payload if k.startswith("shipping_")): "bogus"}
        self.assertContains(self.client.post(reverse("cart:checkout"), bad_ship), "SHIPPING OPTION")

    def test_checkout_ignores_browser_prices(self):
        payload = {**self.valid_checkout_payload(), "total": "1", "price": "1"}
        r = self.client.post(reverse("cart:checkout"), payload, follow=True)
        self.assertContains(r, "Your rental is confirmed!")


class AccountCheckoutTests(JsonPostMixin, TestCase):
    def setUp(self):
        self.posts = make_posts()
        User = get_user_model()
        self.alice = User.objects.create_user("alice", password="pw12345")
        self.bob = User.objects.create_user("bob", password="pw12345")

    def test_checkout_removes_items_and_stays_removed(self):
        self.client.force_login(self.alice)
        r = self.client.post(reverse("cart:checkout"), self.valid_checkout_payload(), follow=True)
        self.assertContains(r, "Your rental is confirmed!")
        self.assertNotContains(r, "Item-01")
        self.assertNotContains(r, "Item-02")
        self.assertContains(r, "Item-03")   # belum dibayar jadi masih ada
        again = self.client.get(reverse("cart:cart"))   # tetap hilang habis reload (User)
        self.assertNotContains(again, "Item-01")
        self.assertEqual(CartItem.objects.filter(cart__user=self.alice).count(), 2)

    def test_other_account_still_has_the_items(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("cart:checkout"), self.valid_checkout_payload())
        other = Client()
        other.force_login(self.bob)
        r = other.get(reverse("cart:cart"))
        self.assertContains(r, "Item-01")
        self.assertContains(r, "Item-02")
        self.assertEqual(CartItem.objects.filter(cart__user=self.bob).count(), 4)

    def test_failed_checkout_keeps_items(self):
        self.client.force_login(self.alice)
        payload = self.valid_checkout_payload()
        payload.pop("payment")
        self.client.post(reverse("cart:checkout"), payload)
        self.assertEqual(CartItem.objects.filter(cart__user=self.alice).count(), 4)


@override_settings(CART_REQUIRE_LOGIN=True, LOGIN_URL="/login/")
class CheckoutLoginRequiredTests(TestCase):
    def test_guest_checkout_redirects_to_login(self):
        make_posts()
        self.assertEqual(self.client.get(reverse("cart:checkout")).status_code, 302)