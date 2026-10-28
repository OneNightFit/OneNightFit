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
    # Produk dari API tidak punya penulis, jadi boleh kosong
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inspo_posts",
    )
    title = models.CharField(max_length=100, blank=True)
    caption = models.CharField(max_length=1000, blank=True)

    # Foto: unggahan user (image) atau URL dari API (image_url)
    image = models.ImageField(upload_to="inspo/posts/", blank=True)
    image_url = models.URLField(blank=True)

    # Data dari Fake Store API
    external_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    tag = models.ForeignKey(
        Tag,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )
    
    hashtags = models.ManyToManyField(Tag, blank=True, related_name="hashtag_posts")
    # Kategori (bisa lebih dari satu), dipakai untuk sorting di tab feed.
    categories = models.ManyToManyField(Tag, blank=True, related_name="category_posts")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # TODO: tag produk ONF (ForeignKey/ManyToMany ke model produk)
    # setelah model Product dari modul Product Catalog tersedia.

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Post {self.pk}"

    @property
    def image_src(self):
        """Foto unggahan user kalau ada, kalau tidak pakai URL dari API."""
        return self.image.url if self.image else self.image_url
    
    @property
    def detail_url(self):
        """URL halaman detail yang benar untuk post ini."""
        from django.urls import reverse
        if self.external_id:      # produk dari API
            return reverse("inspo:detail", args=[self.external_id])
        return reverse("inspo:user_detail", args=[self.pk])   # postingan user

class BookmarkCategory(models.Model):
    """Kategori bookmark buatan user, dibuat saat menyimpan postingan."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inspo_bookmark_categories",
    )
    name = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_bookmark_category_per_user"),
        ]

    def __str__(self):
        return f"{self.name} ({self.user})"

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
    category = models.ForeignKey(
    BookmarkCategory,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
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