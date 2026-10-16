from django.conf import settings
from django.db import models


class Tag(models.Model):
    """Hashtag/kategori, mis. ootd, formal, pesta, y2k."""
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"#{self.name}"


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inspo_posts",
    )
    title = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to="inspo/posts/")
    caption = models.CharField(max_length=300, blank=True)
    tag = models.ForeignKey(
    Tag,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="posts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # TODO: tag produk ONF (ForeignKey/ManyToMany ke model produk)
    # setelah model Product dari modul Product Catalog tersedia.

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post {self.pk} oleh {self.author}"


class Bookmark(models.Model):
    """Simpanan pribadi user. Selalu privat, hanya pemilik yang boleh melihat."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inspo_bookmarks",
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_bookmark_per_user_post"),
        ]

    def __str__(self):
        return f"{self.user} menyimpan post {self.post_id}"


class Board(models.Model):
    """Koleksi buatan user. Bisa privat atau publik."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inspo_boards",
    )
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    is_public = models.BooleanField(default=False)  # default privat
    posts = models.ManyToManyField(Post, blank=True, related_name="boards")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.owner})"

    def is_visible_to(self, user):
        """Pemilik selalu boleh. Orang lain hanya kalau board publik dan sudah login."""
        if not user.is_authenticated:
            return False
        return self.is_public or self.owner_id == user.id