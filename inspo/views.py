from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from inspo.models import Post

CATEGORIES = ["Terbaru", "Terpopuler", "Pesta", "Casual", "Y2K", "Disewakan oleh ONF"]


def feeds(request):
    categories = CATEGORIES

    active_category = request.GET.get("kategori", categories[0])
    if active_category not in categories:
        active_category = categories[0]

    posts = Post.objects.select_related("author", "tag")

    # "Terbaru" dan "Terpopuler" adalah urutan, kategori lain adalah tag.
    if active_category == "Terpopuler":
        # TODO: ganti dengan jumlah like kalau model Like sudah ada.
        posts = posts.annotate(num_saved=Count("bookmarks")).order_by("-num_saved", "-created_at")
    elif active_category != "Terbaru":
        # TODO: "Disewakan oleh ONF" idealnya memakai relasi ke produk ONF.
        # Sementara dicocokkan dengan nama tag.
        posts = posts.filter(tag__name__iexact=active_category)

    query = request.GET.get("q", "").strip()
    if query:
        posts = posts.filter(
            Q(title__icontains=query)
            | Q(caption__icontains=query)
            | Q(tag__name__icontains=query)
        )

    return render(request, "inspo/feeds.html", {
        "categories": categories,
        "active_category": active_category,
        "posts": posts,
        "query": query,
    })


def detail(request, post_id):
    post = get_object_or_404(Post.objects.select_related("author", "tag"), pk=post_id)

    # TODO: ganti komentar dan jumlah like dengan model Comment dan Like.
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

    more_posts = Post.objects.select_related("author", "tag").exclude(pk=post.pk)[:6]

    return render(request, "inspo/detail.html", {
        "post": post,
        "author": post.author.get_full_name() or post.author.get_username(),
        "description": post.caption,
        "likes": 37,
        "comments": comments,
        "comment_count": len(comments) + sum(len(c["replies"]) for c in comments),
        "more_posts": more_posts,
    })