from django.contrib import admin

from inspo.models import Board, Bookmark, Post, Tag, BookmarkCategory


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "tag", "price", "author", "created_at")
    list_filter = ("tag",)
    search_fields = ("title", "caption")


admin.site.register([Tag, Bookmark, BookmarkCategory, Board])
