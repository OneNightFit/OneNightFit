from datetime import timedelta

import requests
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

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
    }


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


def detail(request, post_id):
    data = fetch_json(f"/products/{post_id}")
    if not data:
        raise Http404("Produk tidak ditemukan")
    post = normalize(data)

    all_data = fetch_json("/products") or []
    more_posts = [normalize(p) for p in all_data if p["id"] != post["id"]][:6]

    # TODO: komentar masih dummy karena API tidak menyediakan komentar.
    now = timezone.now()
    comments = [
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

    return render(request, "inspo/detail.html", {
        "post": post,
        "author": "ONF",
        "description": post["caption"],
        "likes": post["rating_count"],
        "comments": comments,
        "comment_count": len(comments) + sum(len(c["replies"]) for c in comments),
        "more_posts": more_posts,
    })