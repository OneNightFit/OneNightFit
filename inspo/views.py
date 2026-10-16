from datetime import timedelta
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

POSTS = [
    {"id": 1, "title": "Blue Stripe and White Denim Street", "caption": "Cardigan stripe + wide-leg denim, santai tapi tetap rapi", "image": "img/model1-ONF.jpg"},
    {"id": 2, "title": "Satin Slip Dress Night Out", "caption": "Dress satin warna champagne, cocok buat dinner atau pesta kecil", "image": "img/model9-ONF.jpg"},
    {"id": 3, "title": "Y2K Mini Skirt Throwback", "caption": "Mini skirt low-rise dipadu baby tee dan aksesoris chunky", "image": "img/model7-ONF.jpg"},
    {"id": 4, "title": "Oversized Blazer Office Chic", "caption": "Blazer oversized cokelat dengan celana kain, kesan profesional yang effortless", "image": "img/model8-ONF.jpg"},
    {"id": 5, "title": "Cargo Pants Street Vibes", "caption": "Cargo pants longgar, crop top, dan sneakers putih untuk hangout seharian", "image": "img/model6-ONF.jpg"},
    {"id": 6, "title": "Floral Midi Weekend Brunch", "caption": "Midi dress motif bunga yang ringan, pas buat brunch atau jalan sore", "image": "img/model2-ONF.jpg"},
    {"id": 7, "title": "Baggy Jeans Y2K Street Style", "caption": "Baggy jeans washed, kemeja crop, dan flanel diikat di pinggang untuk look streetwear ala 2000-an", "image": "img/model3-ONF.jpg"},
]


def feeds(request):
    categories = ["Terbaru", "Terpopuler", "Pesta", "Casual", "Y2K", "Disewakan oleh ONF"]

    active_category = request.GET.get("kategori", categories[0])
    if active_category not in categories:
        active_category = categories[0]

    query = request.GET.get("q", "").strip()
    posts = POSTS
    if query:
        q = query.lower()
        posts = [p for p in posts if q in p["title"].lower() or q in p["caption"].lower()]

    return render(request, "inspo/feeds.html", {
        "categories": categories,
        "active_category": active_category,
        "posts": posts,
        "query": query,
    })


def detail(request, post_id):
    post = next((p for p in POSTS if p["id"] == post_id), None)
    if post is None:
        raise Http404("Postingan tidak ditemukan")

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
        "author": "Fahira",
        "description": "Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "likes": 37,
        "comments": comments,
        "comment_count": len(comments) + sum(len(c["replies"]) for c in comments),
        "more_posts": [p for p in POSTS if p["id"] != post_id],
    })