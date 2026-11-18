from urllib.parse import urlparse

from django.utils.html import strip_tags
from rest_framework import serializers

from catalog.models import Product


class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.CharField(source="seller.username", read_only=True, allow_null=True)
    seller_display = serializers.CharField(read_only=True)
    image_src = serializers.CharField(read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    size_display = serializers.CharField(source="get_size_display", read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)
    is_wishlisted = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    wishlisted_by = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "image", "image_file", "image_src",
            "price", "category", "category_display", "size", "size_display",
            "seller", "seller_display", "average_rating", "rating_count",
            "wishlisted_by", "is_wishlisted", "is_owner",
        ]
        read_only_fields = [
            "id", "seller", "seller_display", "image_src", "category_display",
            "size_display", "average_rating", "rating_count", "wishlisted_by",
            "is_wishlisted", "is_owner",
        ]

    def validate_name(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Name cannot be empty.")
        return value

    def validate_description(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Description cannot be empty.")
        return value

    def validate_image(self, value):
        # The catalog accepts URL images, while uploaded images use image_file.
        if value and urlparse(value).scheme not in {"http", "https"}:
            raise serializers.ValidationError("Image URL must use http or https.")
        return value

    def validate(self, attrs):
        if attrs.get("image") and attrs.get("image_file"):
            raise serializers.ValidationError(
                {"image": "Provide either an image URL or an uploaded image, not both."}
            )
        return attrs

    def update(self, instance, validated_data):
        # Switching image sources should clear the previously saved source.
        if validated_data.get("image"):
            validated_data["image_file"] = None
        elif validated_data.get("image_file"):
            validated_data["image"] = ""
        return super().update(instance, validated_data)

    def get_is_wishlisted(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and obj.wishlisted_by.filter(pk=request.user.pk).exists()
        )

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(
            request and request.user.is_authenticated and obj.seller_id == request.user.pk
        )
