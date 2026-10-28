from django.urls import path
from inspo.views import (
    feeds, detail, upload, user_detail, edit,
    bookmarks, bookmark_toggle, bookmark_categories,
    like_toggle, likes,
)

app_name = "inspo"

urlpatterns = [
    path("", feeds, name="feeds"),
    path("upload/", upload, name="upload"),
    path("like/", like_toggle, name="like_toggle"),
    path("likes/", likes, name="likes"),
    path("post/<int:pk>/", user_detail, name="user_detail"),
    path("post/<int:pk>/edit/", edit, name="edit"),
    path("<int:post_id>/", detail, name="detail"),
    path("bookmarks/", bookmarks, name="bookmarks"),
    path("<int:post_id>/bookmark/", bookmark_toggle, name="bookmark_toggle"),
    path("bookmark-categories/", bookmark_categories, name="bookmark_categories"),
]