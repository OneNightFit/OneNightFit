"""API tests for the catalog's Django REST Framework endpoints."""

import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from authentication.models import Profile
from catalog.models import Product, ProductRating


class CatalogAPITestCase(APITestCase):
    def create_user(self, username, role=Profile.Role.BUYER):
        user = User.objects.create_user(username=username, password="test-password")
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

    def setUp(self):
        self.seller = self.create_user("seller", Profile.Role.SELLER)
        self.other_seller = self.create_user("other-seller", Profile.Role.SELLER)
        self.buyer = self.create_user("buyer")
        self.product = self.create_product(seller=self.seller)
        self.list_url = reverse("api:product-list")
        self.detail_url = reverse("api:product-detail", args=[self.product.pk])
        self.wishlist_url = reverse("api:product-wishlist", args=[self.product.pk])
        self.payload = {
            "name": "Flannel Shirt",
            "description": "A warm flannel shirt.",
            "price": "200000.00",
            "category": "men_clothing",
            "size": "L",
            "image": "https://example.com/flannel.jpg",
        }

    def test_public_list_and_detail_include_product_fields(self):
        list_response = self.client.get(self.list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["id"], str(self.product.pk))
        self.assertEqual(list_response.data[0]["seller"], self.seller.username)
        self.assertEqual(list_response.data[0]["average_rating"], 0.0)
        self.assertEqual(list_response.data[0]["rating_count"], 0)
        self.assertFalse(list_response.data[0]["is_wishlisted"])
        self.assertFalse(list_response.data[0]["is_owner"])

        detail_response = self.client.get(self.detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["name"], self.product.name)

    def test_search_and_category_filters_return_matching_products(self):
        other_product = self.create_product(
            name="Evening Dress",
            seller=self.other_seller,
            description="A dress for a special occasion.",
            category="women_clothing",
        )

        response = self.client.get(self.list_url, {"q": "EVENING"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [str(other_product.pk)])

        response = self.client.get(self.list_url, {"category": "women_clothing"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [str(other_product.pk)])

        response = self.client.get(self.list_url, {"q": "no matching product"})
        self.assertEqual(response.data, [])

    def test_missing_product_returns_not_found(self):
        url = reverse("api:product-detail", args=[uuid.uuid4()])

        self.assertEqual(
            self.client.get(url).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_anonymous_and_buyer_users_cannot_create_products(self):
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Product.objects.count(), 1)

    def test_seller_can_create_product_and_seller_is_taken_from_session(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.post(
            self.list_url,
            {**self.payload, "seller": self.other_seller.username},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(pk=response.data["id"])
        self.assertEqual(created.seller, self.seller)
        self.assertEqual(response.data["seller"], self.seller.username)

    def test_only_owning_seller_can_update_or_delete_product(self):
        self.client.force_authenticate(user=self.other_seller)
        response = self.client.patch(
            self.detail_url, {"name": "Changed by another seller"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(self.detail_url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.seller)
        response = self.client.patch(
            self.detail_url, {"name": "Updated Jacket"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Jacket")

        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_owner_put_requires_all_required_fields(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.put(
            self.detail_url, {"name": "Incomplete replacement"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("description", response.data)

    def test_serializer_rejects_empty_or_markup_only_text_and_unsafe_image_url(self):
        self.client.force_authenticate(user=self.seller)
        invalid_payloads = [
            ({"name": "   "}, "name"),
            ({"name": "<b> </b>"}, "name"),
            ({"description": "<p> </p>"}, "description"),
            ({"image": "javascript:alert(1)"}, "image"),
            ({"category": "unknown"}, "category"),
        ]

        for changes, field in invalid_payloads:
            with self.subTest(field=field, changes=changes):
                response = self.client.post(
                    self.list_url,
                    {**self.payload, **changes},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)

        self.assertEqual(Product.objects.count(), 1)

    def test_seller_cannot_assign_wishlist_or_computed_values(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(
            self.list_url,
            {
                **self.payload,
                "wishlisted_by": [self.buyer.pk],
                "average_rating": 5,
                "rating_count": 99,
                "is_wishlisted": True,
                "is_owner": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Product.objects.get(pk=response.data["id"])
        self.assertEqual(created.wishlisted_by.count(), 0)
        self.assertEqual(response.data["average_rating"], 0.0)
        self.assertEqual(response.data["rating_count"], 0)
        self.assertTrue(response.data["is_owner"])

    def test_wishlist_toggle_requires_login_and_returns_updated_state(self):
        response = self.client.post(self.wishlist_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(self.wishlist_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_wishlisted"])
        self.assertIn(self.buyer.pk, response.data["wishlisted_by"])

        response = self.client.post(self.wishlist_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_wishlisted"])
        self.assertEqual(response.data["wishlisted_by"], [])

    def test_rating_summary_is_included_in_api_response(self):
        ProductRating.objects.create(product=self.product, user=self.buyer, score=4)
        second_buyer = self.create_user("second-buyer")
        ProductRating.objects.create(product=self.product, user=second_buyer, score=5)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["average_rating"], 4.5)
        self.assertEqual(response.data["rating_count"], 2)

