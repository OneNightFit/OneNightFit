import re
from datetime import timedelta

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Post, Tag

API_URL = "https://fakestoreapi.com"

# Label pill di feed -> kategori dari API (None = semua)
CATEGORY_MAP = {
    "Terbaru": None,
    "Terpopuler": None,  # diurutkan berdasarkan rating.count
    "Women": "women's clothing",
    "Man": "men's clothing",
    "Jewelery": "jewelery",
    "Electronics": "electronics",
}

TAG_ALIASES = {
    "Women": ["women's clothing", "Women", "Blouse", "Skirt"],
    "Man": ["men's clothing", "Man", "Shirt", "Jeans", "Blazer", "Hoodie"],
    "Jewelery": ["jewelery", "Jewelery"],
    "Electronics": ["electronics", "Electronics"],
}

ALLOWED_TYPES = ("image/jpeg", "image/png")
MAX_IMAGE_SIZE = 5 * 1024 * 1024
UPLOAD_CATEGORIES = [label for label, api_cat in CATEGORY_MAP.items() if api_cat]


# --------------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------------

def fetch_json(path):
    """Ambil data dari API. Kembalikan None kalau gagal."""
    try:
        res = requests.get(f"{API_URL}{path}", timeout=5)
        res.raise_for_status()
        return res.json()
    except (requests.RequestException, ValueError):
        return None


def normalize(p):
    """Samakan bentuk data API dengan yang dipakai template."""
    rating = p.get("rating") or {}
    return {
        "id": p["id"],
        "title": p["title"],
        "caption": p["description"],
        "image": p["image"],          # sudah berupa URL penuh
        "price": p["price"],
        "category": p["category"],
        "rating_count": rating.get("count", 0),
        "url": reverse("inspo:detail", args=[p["id"]]),
        "is_user_post": False,
    }


def normalize_user_post(p):
    """Bentuk yang sama untuk postingan buatan user (model Post)."""
    return {
        "id": p.pk,
        "title": p.title,
        "caption": p.caption,
        "image": p.image_src,
        "price": p.price,
        "category": p.tag.name if p.tag else "",
        "rating_count": 0,
        "url": reverse("inspo:user_detail", args=[p.pk]),
        "is_user_post": True,
    }


def dummy_comments():
    # TODO: komentar masih dummy karena API tidak menyediakan komentar.
    now = timezone.now()
    return [
        {
            "user": "Fahira",
            "text": "Outfit-nya cakep banget, ini ukuran apa ya?",
            "posted_at": now - timedelta(hours=2),
            "likes": 3,
            "replies": [
                {"user": "Kayla", "text": "Ukuran M kak, muat banget!", "posted_at": now - timedelta(minutes=45), "likes": 1},
            ],
        },
        {
            "user": "Alifah",
            "text": "Cocok dipakai buat acara kampus nih.",
            "posted_at": now - timedelta(days=1),
            "likes": 0,
            "replies": [],
        },
    ]


def _clean_hashtags(raw):
    """'ootd, Formal ,y2k' -> ['ootd', 'formal', 'y2k'] (maks. 5, tanpa duplikat)."""
    result = []
    for part in raw.split(","):
        name = re.sub(r"[^\w]", "", part.strip())[:30].lower()
        if name and name not in result:
            result.append(name)
    return result[:5]


# --------------------------------------------------------------------------
# Feed & detail
# --------------------------------------------------------------------------

def feeds(request):
    categories = list(CATEGORY_MAP.keys())

    active_category = request.GET.get("kategori", categories[0])
    if active_category not in CATEGORY_MAP:
        active_category = categories[0]

    data = fetch_json("/products")
    api_error = data is None
    posts = [normalize(p) for p in (data or [])]

    api_category = CATEGORY_MAP[active_category]
    if api_category:
        posts = [p for p in posts if p["category"] == api_category]

    # Postingan user dari database, ikut difilter per kategori
    user_posts = Post.objects.filter(author__isnull=False).select_related("tag")
    aliases = TAG_ALIASES.get(active_category)
    if aliases:
        cond = Q()
        for name in aliases:
            cond |= Q(tag__name__iexact=name) | Q(categories__name__iexact=name)
        user_posts = user_posts.filter(cond).distinct()
    posts = [normalize_user_post(p) for p in user_posts[:50]] + posts

    if active_category == "Terpopuler":
        posts.sort(key=lambda p: p["rating_count"], reverse=True)

    query = request.GET.get("q", "").strip()
    if query:
        q = query.lower()
        posts = [p for p in posts if q in p["title"].lower() or q in p["caption"].lower()]

    return render(request, "inspo/feeds.html", {
        "categories": categories,
        "active_category": active_category,
        "posts": posts,
        "query": query,
        "api_error": api_error,
    })


def _more_posts(exclude_api_id=None):
    all_data = fetch_json("/products") or []
    return [normalize(p) for p in all_data if p["id"] != exclude_api_id][:6]


def detail(request, post_id):
    data = fetch_json(f"/products/{post_id}")
    if not data:
        raise Http404("Produk tidak ditemukan")
    post = normalize(data)
    comments = dummy_comments()

    return render(request, "inspo/detail.html", {
        "post": post,
        "author": "ONF",
        "description": post["caption"],
        "likes": post["rating_count"],
        "comments": comments,
        "comment_count": len(comments) + sum(len(c["replies"]) for c in comments),
        "more_posts": _more_posts(exclude_api_id=post["id"]),
    })


def user_detail(request, pk):
    obj = get_object_or_404(
        Post.objects.select_related("author", "tag"), pk=pk, author__isnull=False
    )
    post = normalize_user_post(obj)
    comments = dummy_comments()

    return render(request, "inspo/detail.html", {
        "post": post,
        "author": obj.author.get_username(),
        "description": obj.caption,
        "likes": 0,
        "comments": comments,
        "comment_count": len(comments) + sum(len(c["replies"]) for c in comments),
        "more_posts": _more_posts(),
        "is_owner": request.user.is_authenticated and obj.author_id == request.user.id,
    })


# --------------------------------------------------------------------------
# Upload & Edit
# --------------------------------------------------------------------------

def _validate_image(image):
    """Kembalikan pesan error (str) atau None kalau foto valid."""
    if image.content_type not in ALLOWED_TYPES:
        return "Foto harus berformat JPG atau PNG."
    if image.size > MAX_IMAGE_SIZE:
        return "Ukuran foto maksimal 5 MB."
    try:
        Image.open(image).verify()   # pastikan benar-benar gambar
        image.seek(0)
    except Exception:
        return "File yang diunggah bukan gambar yang valid."
    return None


def _form_context(mode, errors, title, caption, hashtags, selected, current_image="", post=None):
    return {
        "mode": mode,                      # "create" atau "edit"
        "post": post,
        "errors": errors,
        "title": title,
        "caption": caption,
        "hashtags": hashtags,
        "selected_categories": selected,
        "current_image": current_image,
        "categories": UPLOAD_CATEGORIES,
        "products": [],   # TODO: isi setelah model Product tersedia
    }


@login_required
def upload(request):
    errors = []
    title = caption = hashtags_raw = ""
    selected = []

    if request.method == "POST":
        image = request.FILES.get("image")
        title = request.POST.get("title", "").strip()[:100]
        caption = request.POST.get("caption", "").strip()[:300]
        hashtags_raw = request.POST.get("hashtags", "")
        selected = [k for k in request.POST.getlist("kategori") if k in UPLOAD_CATEGORIES]

        if not title:
            errors.append("Judul wajib diisi.")
        if not image:
            errors.append("Foto wajib diunggah.")
        else:
            err = _validate_image(image)
            if err:
                errors.append(err)

        if not errors:
            cat_tags = [Tag.objects.get_or_create(name=c)[0] for c in selected]

            post = Post.objects.create(
                author=request.user,
                title=title,
                caption=caption,
                image=image,
                tag=cat_tags[0] if cat_tags else None,   # kategori utama (kompatibel dengan data lama)
            )
            post.categories.set(cat_tags)

            tag_objs = [Tag.objects.get_or_create(name=n)[0] for n in _clean_hashtags(hashtags_raw)]
            post.hashtags.set(tag_objs)

            messages.success(request, "Postingan berhasil dibagikan.")
            return redirect("inspo:user_detail", pk=post.pk)

    return render(request, "inspo/upload.html",
                  _form_context("create", errors, title, caption, hashtags_raw, selected))


@login_required
def edit(request, pk):
    # author=request.user: postingan orang lain otomatis 404, jadi tidak bisa diedit lewat URL
    post = get_object_or_404(Post.objects.select_related("tag"), pk=pk, author=request.user)
    errors = []

    if request.method == "POST":
        image = request.FILES.get("image")          # opsional saat edit
        title = request.POST.get("title", "").strip()[:100]
        caption = request.POST.get("caption", "").strip()[:300]
        hashtags_raw = request.POST.get("hashtags", "")
        selected = [k for k in request.POST.getlist("kategori") if k in UPLOAD_CATEGORIES]

        if not title:
            errors.append("Judul wajib diisi.")
        if image:
            err = _validate_image(image)
            if err:
                errors.append(err)

        if not errors:
            cat_tags = [Tag.objects.get_or_create(name=c)[0] for c in selected]

            post.title = title
            post.caption = caption
            post.tag = cat_tags[0] if cat_tags else None
            if image:
                post.image = image                   # tanpa file baru, foto lama dipertahankan
            post.save()
            post.categories.set(cat_tags)

            tag_objs = [Tag.objects.get_or_create(name=n)[0] for n in _clean_hashtags(hashtags_raw)]
            post.hashtags.set(tag_objs)

            messages.success(request, "Perubahan berhasil disimpan.")
            return redirect("inspo:user_detail", pk=post.pk)
    else:
        title = post.title
        caption = post.caption
        hashtags_raw = ",".join(post.hashtags.values_list("name", flat=True))
        names = set(post.categories.values_list("name", flat=True))
        if post.tag:
            names.add(post.tag.name)
        selected = [c for c in UPLOAD_CATEGORIES if c in names]

    return render(request, "inspo/upload.html", _form_context(
        "edit", errors, title, caption, hashtags_raw, selected,
        current_image=post.image_src, post=post,
    ))