"""Unit tests for catalog models, forms, and HTTP endpoints.

Test names follow Given/When/Then so each case states its setup, action, and
expected result explicitly.
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from authentication.models import Profile
from cart.models import Cart, CartItem
from catalog.forms import ProductForm
from catalog.models import Product, ProductRating


class CatalogTestDataMixin:
    """Shared fixtures for catalog unit tests."""

    def create_user(self, username, role=Profile.Role.BUYER, **kwargs):
        user = User.objects.create_user(username=username, password="password123", **kwargs)
        user.profile.role = role
        user.profile.save(update_fields=["role"])
        return user

    def create_product(self, *, name="Classic Jacket", seller=None, **kwargs):
        defaults = {
            "description": "A comfortable jacket for rent.",
            "price": Decimal("125000.00"),
            "category": "men_clothing",
            "size": "M",
        }
        defaults.update(kwargs)
        return Product.objects.create(name=name, seller=seller, **defaults)


class ProductModelTests(CatalogTestDataMixin, TestCase):
    def setUp(self):
        self.seller = self.create_user("seller", Profile.Role.SELLER, first_name="Seller Name")
        self.buyer = self.create_user("buyer")
        self.product = self.create_product(seller=self.seller)

    def test_given_product_when_converted_to_string_then_name_is_returned(self):
        self.assertEqual(str(self.product), "Classic Jacket")

    def test_given_seller_with_shop_name_when_reading_seller_display_then_shop_name_is_returned(self):
        self.seller.profile.shop_name = "Closet Studio"
        self.seller.profile.save(update_fields=["shop_name"])

        self.assertEqual(self.product.seller_display, "Closet Studio")

    def test_given_seller_without_shop_name_when_reading_seller_display_then_full_name_is_returned(self):
        self.assertEqual(self.product.seller_display, "Seller Name")

    def test_given_product_without_seller_when_reading_seller_display_then_dash_is_returned(self):
        self.product.seller = None

        self.assertEqual(self.product.seller_display, "-")

    def test_given_product_without_image_when_reading_image_src_then_empty_string_is_returned(self):
        self.assertEqual(self.product.image_src, "")

    def test_given_external_image_url_when_reading_image_src_then_url_is_returned(self):
        self.product.image = "https://example.com/jacket.jpg"

        self.assertEqual(self.product.image_src, "https://example.com/jacket.jpg")

    def test_given_product_without_ratings_when_reading_rating_properties_then_zero_values_are_returned(self):
        self.assertEqual(self.product.average_rating, 0.0)
        self.assertEqual(self.product.rating_count, 0)

    def test_given_multiple_ratings_when_reading_rating_properties_then_average_and_count_are_returned(self):
        second_buyer = self.create_user("second-buyer")
        ProductRating.objects.create(product=self.product, user=self.buyer, score=4)
        ProductRating.objects.create(product=self.product, user=second_buyer, score=5)

        self.assertEqual(self.product.average_rating, 4.5)
        self.assertEqual(self.product.rating_count, 2)

    def test_given_annotated_ratings_when_reading_properties_then_annotations_are_used(self):
        self.product.avg_score = 4.26
        self.product.ratings_cnt = 3

        self.assertEqual(self.product.average_rating, 4.3)
        self.assertEqual(self.product.rating_count, 3)

    def test_given_unrated_product_when_reading_annotated_average_then_zero_is_returned(self):
        self.product.avg_score = None

        self.assertEqual(self.product.average_rating, 0.0)

    def test_given_anonymous_user_when_checking_wishlist_then_false_is_returned(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(self.product.is_wishlisted_by(AnonymousUser()))

    def test_given_product_not_wishlisted_by_user_when_checking_wishlist_then_false_is_returned(self):
        self.assertFalse(self.product.is_wishlisted_by(self.buyer))

    def test_given_product_wishlisted_by_user_when_checking_wishlist_then_true_is_returned(self):
        self.product.wishlisted_by.add(self.buyer)

        self.assertTrue(self.product.is_wishlisted_by(self.buyer))

    def test_given_rating_when_converted_to_string_then_user_product_and_score_are_included(self):
        rating = ProductRating.objects.create(product=self.product, user=self.buyer, score=4)

        self.assertEqual(str(rating), "buyer rated Classic Jacket 4/5")


class ProductFormTests(TestCase):
    def setUp(self):
        self.valid_data = {
            "name": "Flannel Shirt",
            "category": "men_clothing",
            "size": "L",
            "description": "A warm flannel shirt.",
            "price": "200000.00",
            "image_source": "url",
            "image": "https://example.com/flannel.jpg",
        }

    def test_given_valid_product_data_when_validating_form_then_form_is_valid(self):
        form = ProductForm(data=self.valid_data)

        self.assertTrue(form.is_valid(), form.errors)

    def test_given_missing_required_price_when_validating_form_then_price_error_is_returned(self):
        data = {**self.valid_data}
        data.pop("price")
        form = ProductForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

    def test_given_invalid_category_when_validating_form_then_category_error_is_returned(self):
        form = ProductForm(data={**self.valid_data, "category": "invalid-category"})

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_given_invalid_price_when_validating_form_then_price_error_is_returned(self):
        form = ProductForm(data={**self.valid_data, "price": "not-a-price"})

        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

    def test_given_valid_url_image_data_when_saving_form_then_product_keeps_url_and_has_no_upload(self):
        form = ProductForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

        product = form.save()

        self.assertEqual(product.image, "https://example.com/flannel.jpg")
        self.assertFalse(product.image_file)


class CatalogPageViewTests(CatalogTestDataMixin, TestCase):
    def setUp(self):
        self.seller = self.create_user("catalog-seller", Profile.Role.SELLER)
        self.other_seller = self.create_user("other-seller", Profile.Role.SELLER)
        self.buyer = self.create_user("catalog-buyer")
        self.product = self.create_product(seller=self.seller, name="Seller Jacket")
        self.other_product = self.create_product(
            seller=self.other_seller,
            name="Other Skirt",
            category="women_clothing",
        )

    def test_given_catalog_products_when_anonymous_user_opens_catalog_then_page_and_filter_context_are_rendered(self):
        response = self.client.get(reverse("catalog:catalog_list"), {"category": ["men_clothing", "women_clothing"], "q": " jacket "})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/catalog.html")
        self.assertEqual(response.context["selected_categories"], ["men_clothing", "women_clothing"])
        self.assertEqual(response.context["search_query"], "jacket")
        self.assertEqual(dict((code, count) for code, _name, count in response.context["categories"])["men_clothing"], 1)

    def test_given_seller_when_opening_catalog_then_only_own_product_counts_are_shown(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("catalog:catalog_list"))

        self.assertEqual(response.status_code, 200)
        category_counts = {code: count for code, _name, count in response.context["categories"]}
        self.assertEqual(category_counts["men_clothing"], 1)
        self.assertEqual(category_counts["women_clothing"], 0)
        self.assertContains(response, "Add New Product")

    def test_given_buyer_when_opening_catalog_then_seller_controls_are_not_rendered(self):
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("catalog:catalog_list"))

        self.assertEqual(response.status_code, 200)
        # The client-side empty-state message mentions this label in JavaScript;
        # assert the actual seller-only button is absent from the rendered page.
        self.assertNotContains(response, 'popovertarget="add-product-modal"')


class ProductJsonViewTests(CatalogTestDataMixin, TestCase):
    def setUp(self):
        self.seller = self.create_user("json-seller", Profile.Role.SELLER, first_name="Json Seller")
        self.buyer = self.create_user("json-buyer")
        self.product = self.create_product(seller=self.seller, image="https://example.com/item.jpg")
        self.other_product = self.create_product(
            seller=self.create_user("json-other-seller", Profile.Role.SELLER),
            name="Women Coat",
            category="women_clothing",
            description="A long wool coat.",
        )
        ProductRating.objects.create(product=self.product, user=self.buyer, score=4)

    def test_given_existing_product_when_requesting_detail_then_json_product_and_ratings_are_returned(self):
        response = self.client.get(reverse("catalog:product_detail", args=[self.product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["pk"], str(self.product.pk))
        self.assertEqual(response.json()["fields"]["average_rating"], 4.0)
        self.assertEqual(response.json()["fields"]["rating_count"], 1)
        self.assertEqual(response.json()["fields"]["seller_display"], "Json Seller")

    def test_given_unknown_product_id_when_requesting_detail_then_not_found_is_returned(self):
        response = self.client.get(reverse("catalog:product_detail", args=["00000000-0000-0000-0000-000000000000"]))

        self.assertEqual(response.status_code, 404)

    def test_given_products_when_requesting_json_then_product_payloads_are_returned(self):
        response = self.client.get(reverse("catalog:get_products_json"))

        self.assertEqual(response.status_code, 200)
        products = response.json()
        self.assertEqual({item["pk"] for item in products}, {str(self.product.pk), str(self.other_product.pk)})
        product_data = next(item["fields"] for item in products if item["pk"] == str(self.product.pk))
        self.assertEqual(product_data["image"], "https://example.com/item.jpg")
        self.assertEqual(product_data["image_url"], "https://example.com/item.jpg")
        self.assertFalse(product_data["is_wishlisted"])
        self.assertFalse(product_data["is_in_cart"])
        self.assertFalse(product_data["is_owner"])

    def test_given_category_filter_when_requesting_json_then_only_matching_category_is_returned(self):
        response = self.client.get(reverse("catalog:get_products_json"), {"category": ["women_clothing"]})

        self.assertEqual([item["pk"] for item in response.json()], [str(self.other_product.pk)])

    def test_given_search_query_when_requesting_json_then_name_or_description_matches_are_returned(self):
        response = self.client.get(reverse("catalog:get_products_json"), {"q": "  wool  "})

        self.assertEqual([item["pk"] for item in response.json()], [str(self.other_product.pk)])

    def test_given_seller_when_requesting_json_then_only_own_products_are_returned(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("catalog:get_products_json"))

        self.assertEqual([item["pk"] for item in response.json()], [str(self.product.pk)])

    def test_given_unavailable_product_when_requesting_json_then_product_is_excluded(self):
        with patch("catalog.views.unavailable_product_ids", return_value={self.product.pk}):
            response = self.client.get(reverse("catalog:get_products_json"))

        self.assertEqual([item["pk"] for item in response.json()], [str(self.other_product.pk)])

    def test_given_authenticated_user_with_wishlist_and_cart_item_when_requesting_json_then_state_flags_are_true(self):
        self.client.force_login(self.buyer)
        self.product.wishlisted_by.add(self.buyer)
        cart = Cart.objects.create(user=self.buyer)
        CartItem.objects.create(cart=cart, product=self.product)

        response = self.client.get(reverse("catalog:get_products_json"))

        product_data = next(item["fields"] for item in response.json() if item["pk"] == str(self.product.pk))
        self.assertTrue(product_data["is_wishlisted"])
        self.assertTrue(product_data["is_in_cart"])

    def test_given_product_owned_by_authenticated_seller_when_requesting_json_then_owner_flag_is_true(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("catalog:get_products_json"))

        self.assertTrue(response.json()[0]["fields"]["is_owner"])


class ProductCrudViewTests(CatalogTestDataMixin, TestCase):
    def setUp(self):
        self.seller = self.create_user("crud-seller", Profile.Role.SELLER)
        self.other_seller = self.create_user("crud-other-seller", Profile.Role.SELLER)
        self.buyer = self.create_user("crud-buyer")
        self.product = self.create_product(seller=self.seller)
        self.valid_data = {
            "name": "New Rental Dress",
            "category": "women_clothing",
            "size": "S",
            "description": "A dress for a special evening.",
            "price": "300000.00",
            "image_source": "url",
            "image": "https://example.com/dress.jpg",
        }

    def test_given_seller_and_valid_data_when_creating_product_then_created_response_and_seller_assignment_are_returned(self):
        self.client.force_login(self.seller)

        response = self.client.post(reverse("catalog:create_product_ajax"), self.valid_data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "Produk berhasil ditambahkan.")
        created_product = Product.objects.get(pk=response.json()["pk"])
        self.assertEqual(created_product.seller, self.seller)
        self.assertEqual(created_product.name, "New Rental Dress")

    def test_given_non_seller_when_creating_product_then_forbidden_response_is_returned(self):
        self.client.force_login(self.buyer)

        response = self.client.post(reverse("catalog:create_product_ajax"), self.valid_data)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Product.objects.count(), 1)

    def test_given_anonymous_user_when_creating_product_then_forbidden_response_is_returned(self):
        response = self.client.post(reverse("catalog:create_product_ajax"), self.valid_data)

        self.assertEqual(response.status_code, 403)

    def test_given_seller_and_invalid_data_when_creating_product_then_validation_errors_are_returned(self):
        self.client.force_login(self.seller)

        response = self.client.post(reverse("catalog:create_product_ajax"), {**self.valid_data, "price": "bad"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("price", response.json()["errors"])
        self.assertEqual(Product.objects.count(), 1)

    def test_given_non_post_request_when_creating_product_then_method_not_allowed_is_returned(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("catalog:create_product_ajax"))

        self.assertEqual(response.status_code, 405)

    def test_given_owner_and_valid_data_when_editing_product_then_product_is_updated(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("catalog:edit_product_ajax", args=[self.product.pk]),
            {**self.valid_data, "name": "Updated Jacket"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pk"], str(self.product.pk))
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Jacket")
        self.assertEqual(self.product.seller, self.seller)

    def test_given_invalid_data_when_editing_product_then_validation_errors_are_returned_and_product_is_unchanged(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("catalog:edit_product_ajax", args=[self.product.pk]),
            {**self.valid_data, "price": "bad"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("price", response.json()["errors"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Classic Jacket")

    def test_given_other_seller_when_editing_product_then_forbidden_response_is_returned(self):
        self.client.force_login(self.other_seller)

        response = self.client.post(reverse("catalog:edit_product_ajax", args=[self.product.pk]), self.valid_data)

        self.assertEqual(response.status_code, 403)

    def test_given_buyer_when_editing_product_then_forbidden_response_is_returned(self):
        self.client.force_login(self.buyer)

        response = self.client.post(reverse("catalog:edit_product_ajax", args=[self.product.pk]), self.valid_data)

        self.assertEqual(response.status_code, 403)

    def test_given_unknown_product_when_editing_then_not_found_is_returned(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("catalog:edit_product_ajax", args=["00000000-0000-0000-0000-000000000000"]),
            self.valid_data,
        )

        self.assertEqual(response.status_code, 404)

    def test_given_owner_when_deleting_product_then_success_response_and_product_removal_are_returned(self):
        self.client.force_login(self.seller)

        response = self.client.post(reverse("catalog:delete_product_ajax", args=[self.product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Produk berhasil dihapus.")
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_given_other_seller_when_deleting_product_then_forbidden_response_and_product_remains(self):
        self.client.force_login(self.other_seller)

        response = self.client.post(reverse("catalog:delete_product_ajax", args=[self.product.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_given_buyer_when_deleting_product_then_forbidden_response_is_returned(self):
        self.client.force_login(self.buyer)

        response = self.client.post(reverse("catalog:delete_product_ajax", args=[self.product.pk]))

        self.assertEqual(response.status_code, 403)

    def test_given_unknown_product_when_deleting_then_not_found_is_returned(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("catalog:delete_product_ajax", args=["00000000-0000-0000-0000-000000000000"])
        )

        self.assertEqual(response.status_code, 404)

    def test_given_non_post_request_when_deleting_product_then_method_not_allowed_is_returned(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("catalog:delete_product_ajax", args=[self.product.pk]))

        self.assertEqual(response.status_code, 405)


class WishlistViewTests(CatalogTestDataMixin, TestCase):
    def setUp(self):
        self.buyer = self.create_user("wishlist-buyer")
        self.product = self.create_product()

    def test_given_authenticated_user_not_wishlisting_product_when_posting_toggle_then_product_is_added(self):
        self.client.force_login(self.buyer)

        response = self.client.post(reverse("catalog:toggle_wishlist", args=[self.product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_wishlisted"])
        self.assertTrue(self.product.wishlisted_by.filter(pk=self.buyer.pk).exists())

    def test_given_authenticated_user_already_wishlisting_product_when_posting_toggle_then_product_is_removed(self):
        self.client.force_login(self.buyer)
        self.product.wishlisted_by.add(self.buyer)

        response = self.client.post(reverse("catalog:toggle_wishlist", args=[self.product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_wishlisted"])
        self.assertFalse(self.product.wishlisted_by.filter(pk=self.buyer.pk).exists())

    def test_given_anonymous_user_requesting_json_when_posting_toggle_then_unauthorized_json_is_returned(self):
        response = self.client.post(
            reverse("catalog:toggle_wishlist", args=[self.product.pk]),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["message"], "Please login to continue.")

    def test_given_anonymous_user_requesting_html_when_posting_toggle_then_login_redirect_is_returned(self):
        response = self.client.post(reverse("catalog:toggle_wishlist", args=[self.product.pk]))

        self.assertRedirects(response, reverse("authentication:login"))

    def test_given_unknown_product_when_posting_toggle_then_not_found_is_returned(self):
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("catalog:toggle_wishlist", args=["00000000-0000-0000-0000-000000000000"])
        )

        self.assertEqual(response.status_code, 404)

    def test_given_non_post_request_when_toggling_wishlist_then_method_not_allowed_is_returned(self):
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("catalog:toggle_wishlist", args=[self.product.pk]))

        self.assertEqual(response.status_code, 405)


class AddToCartViewTests(CatalogTestDataMixin, TestCase):
    def setUp(self):
        self.buyer = self.create_user("cart-buyer")
        self.product = self.create_product()

    def test_given_anonymous_user_when_adding_product_to_cart_then_unauthorized_response_is_returned(self):
        response = self.client.post(reverse("catalog:add_to_cart", args=[self.product.pk]))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["message"], "Harap login terlebih dahulu.")

    def test_given_authenticated_user_and_empty_session_cart_when_adding_product_then_product_is_added(self):
        self.client.force_login(self.buyer)

        response = self.client.post(reverse("catalog:add_to_cart", args=[self.product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.session["cart"][str(self.product.pk)],
            {"name": self.product.name, "price": str(self.product.price), "quantity": 1},
        )

    def test_given_product_already_in_session_cart_when_adding_again_then_quantity_is_incremented(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse("catalog:add_to_cart", args=[self.product.pk]))

        response = self.client.post(reverse("catalog:add_to_cart", args=[self.product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["cart"][str(self.product.pk)]["quantity"], 2)

    def test_given_unknown_product_when_adding_to_cart_then_not_found_is_returned(self):
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("catalog:add_to_cart", args=["00000000-0000-0000-0000-000000000000"])
        )

        self.assertEqual(response.status_code, 404)
