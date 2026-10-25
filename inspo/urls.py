from django.urls import path
from inspo.views import feeds, detail, upload, user_detail, edit

app_name = "inspo"

urlpatterns = [
    path("", feeds, name="feeds"),
    path("upload/", upload, name="upload"),
    path("post/<int:pk>/", user_detail, name="user_detail"),
    path("post/<int:pk>/edit/", edit, name="edit"),
    path("<int:post_id>/", detail, name="detail"),
]