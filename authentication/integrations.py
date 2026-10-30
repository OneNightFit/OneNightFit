"""
Penghubung ke modul lain (Products/catalog dan Inspo).

Aturan: hanya file ini yang tahu nama model/field modul lain. Kalau model teman berubah,
cukup edit file ini. Arah ketergantungan SATU ARAH: authentication membaca modul lain,
modul lain tidak meng-import authentication.

Semua fungsi mengembalikan None kalau modelnya belum ada, sehingga dashboard tampil
kosong (tidak error) walaupun modul teman belum digabung.
"""
from django.apps import apps
from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse


def _has_field(model, name):
    return any(f.name == name for f in model._meta.get_fields())


def find_model(name, required_field):
    """Cari model bernama `name` yang punya field `required_field`. None kalau tidak ada."""
    for model in apps.get_models():
        if model.__name__ == name and _has_field(model, required_field):
            return model
    return None


# ======================================================================
# Products (catalog)
# ======================================================================
def buyer_wishlist(user):
    """Produk yang di-wishlist buyer (Product.wishlisted_by = ManyToMany ke User)."""
    Product = find_model("Product", "wishlisted_by")
    return Product.objects.filter(wishlisted_by=user) if Product else None


def seller_products(user):
    """Produk yang di-upload seller. Butuh field Product.seller (ForeignKey ke User)."""
    Product = find_model("Product", "seller")
    return Product.objects.filter(seller=user) if Product else None


# ======================================================================
# Inspo: like & bookmark
# ======================================================================
INSPO_ITEM_MODEL = "Post"  # model post Inspo (lihat Bookmark.post -> Post)


def find_user_relation(keywords, only_app=None):
    """
    Cari relasi "user menyukai/menyimpan Post". Dua bentuk umum yang dikenali:
      (a) ManyToMany ke User di model Post, mis. Post.liked_by
      (b) model terpisah dengan FK ke User dan FK ke Post, mis. Like(user, post)
    Hanya relasi yang menyangkut model Post yang diterima, supaya like komentar atau
    wishlist produk tidak ikut terbaca sebagai "Liked Inspo".
    Kembalian: ("m2m", model, field_name) | ("model", model, (user_field, post_field)) | None
    """
    User = get_user_model()
    best, best_score = None, -1
    for model in apps.get_models():
        if only_app and model._meta.app_label != only_app:
            continue
        if model._meta.app_label == "authentication":
            continue
        fields = list(model._meta.get_fields())
        name = model.__name__

        # (a) ManyToMany ke User pada model Post
        if name == INSPO_ITEM_MODEL:
            for f in fields:
                if (f.many_to_many and not f.auto_created and f.related_model is User
                        and any(k in f.name.lower() for k in keywords)) and best_score < 1:
                    best, best_score = ("m2m", model, f.name), 1

        # (b) model terpisah yang menunjuk ke User dan ke Post
        if any(k in name.lower() for k in keywords):
            user_fk = next((f for f in fields if f.many_to_one and f.related_model is User), None)
            post_fk = next(
                (f for f in fields
                 if f.many_to_one and f.related_model.__name__ == INSPO_ITEM_MODEL),
                None,
            )
            if user_fk and post_fk:
                score = 3 if name.lower() in keywords else 2  # nama persis ("Like") lebih diutamakan
                if score > best_score:
                    best, best_score = ("model", model, (user_fk.name, post_fk.name)), score
    return best


def user_items(keywords, user):
    """Daftar Post yang di-like/di-bookmark user. None kalau relasinya tidak terdeteksi."""
    relation = find_user_relation(keywords, only_app="inspo") or find_user_relation(keywords)
    if relation is None:
        return None
    kind, model, spec = relation
    if kind == "m2m":
        return list(model.objects.filter(**{spec: user}).order_by("-pk"))
    user_field, post_field = spec
    rows = model.objects.filter(**{user_field: user}).select_related(post_field).order_by("-pk")
    return [getattr(row, post_field) for row in rows]


def inspo_bookmarks(user):
    """
    Post yang disimpan user. Memakai relasi pasti dari inspo.Bookmark
    (Bookmark.user related_name="inspo_bookmarks", Bookmark.post -> Post); kalau relasi itu
    tidak ada, jatuh ke deteksi otomatis.
    """
    bookmarks = getattr(user, "inspo_bookmarks", None)
    if bookmarks is not None:
        return [b.post for b in bookmarks.select_related("post").order_by("-created_at")]
    return user_items(("bookmark", "saved"), user)


def inspo_likes(user):
    """Post yang di-like user (dideteksi otomatis: Like(user, post) atau Post.liked_by)."""
    return user_items(("like",), user)


# ----------------------------------------------------------------------
# Inspo: data untuk grid di tab Activity (memakai partial milik inspo)
# ----------------------------------------------------------------------
# Samakan dengan isi SORTS di inspo/views.py kalau nama field waktunya berbeda.
SORT_FIELDS = {"terbaru": "-created_at", "terlama": "created_at"}


def _inspo_model(name):
    """Cari model di app inspo berdasarkan nama. None kalau belum ada."""
    return next(
        (m for m in apps.get_models()
         if m.__name__ == name and m._meta.app_label == "inspo"),
        None,
    )


def inspo_bookmark_items(user, category="", sort="terbaru"):
    """Queryset Bookmark milik user untuk grid. None kalau relasinya tidak ada."""
    bookmarks = getattr(user, "inspo_bookmarks", None)   # related_name Bookmark.user
    if bookmarks is None:
        return None
    qs = bookmarks.select_related("post", "post__author", "post__tag", "category")
    if category:
        qs = qs.filter(category__name=category)
    return qs.order_by(SORT_FIELDS.get(sort, "-created_at"))


def inspo_bookmark_categories(user):
    """Kategori bookmark milik user (untuk pill filter). Kosong kalau modelnya tidak ada."""
    Category = _inspo_model("BookmarkCategory")
    return Category.objects.filter(user=user) if Category else []


def inspo_like_items(user):
    """Queryset Like milik user untuk grid. None kalau model Like tidak ada."""
    Like = _inspo_model("Like")
    if Like is None:
        return None
    return Like.objects.filter(user=user).select_related("post", "post__author", "post__tag")


# ======================================================================
# Ubah item apa pun jadi "kartu" sederhana untuk template
# ======================================================================
def _first_attr(obj, names):
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return value
    return None


def item_card(item, detail_names=(), remove_name=None):
    """
    Rangkum item ke dict {title, image, url, remove_url} agar template tidak perlu tahu nama
    field aslinya. Field yang tidak ada menjadi string kosong (tidak error).
    """
    title = _first_attr(item, ("name", "title", "caption")) or str(item)

    image = ""
    raw_image = _first_attr(item, ("image", "image_url", "photo"))
    if raw_image:
        try:
            image = raw_image.url if hasattr(raw_image, "url") else str(raw_image)
        except ValueError:  # ImageField tanpa file
            image = ""

    url = ""
    if hasattr(item, "get_absolute_url"):
        try:
            url = item.get_absolute_url() or ""
        except NoReverseMatch:
            url = ""
    if not url:
        for name in detail_names:
            try:
                url = reverse(name, args=[item.pk])
                break
            except NoReverseMatch:
                continue

    remove_url = ""
    if remove_name:
        try:
            remove_url = reverse(remove_name, args=[item.pk])
        except NoReverseMatch:
            remove_url = ""

    return {"id": str(item.pk),"title": str(title), "image": image, "url": url, "remove_url": remove_url}


PRODUCT_DETAIL_URL_NAMES = ("catalog:product_detail", "catalog:detail")


def product_card(product):
    # Tombol "Remove" memakai toggle_wishlist milik Products (menghapus kalau sudah ada)
    return item_card(
        product,
        detail_names=PRODUCT_DETAIL_URL_NAMES,
        remove_name="catalog:toggle_wishlist",
    )

def inspo_card(post):
    return item_card(post, detail_names=("inspo:detail",))