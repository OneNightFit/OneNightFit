from django.urls import path
from inspo.views import feeds, detail

app_name = "inspo"

urlpatterns = [
    path("", feeds, name="feeds"),
    path("<int:post_id>/", detail, name="detail"),
]