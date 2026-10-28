from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "shop_name", "city")
    list_filter = ("role",)
    search_fields = ("user__username", "user__first_name", "shop_name", "city")
