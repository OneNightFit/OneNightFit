import io
import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from inspo.models import Board, Bookmark, BookmarkCategory, Post, Tag
from inspo.views import _clean_hashtags

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp()


# --------------------------------------------------------------------------
# Helper untuk test
# --------------------------------------------------------------------------

def make_png(name="foto.png", size=(10, 10)):
    """Bikin file PNG valid di memori (lolos Image.verify)."""
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def api_product(pk=1, title="Kaos API", category="men's clothing", count=10):
    return {
        "id": pk,
        "title": title,
        "description": f"Deskripsi {title}",
        "image": f"https://example.com/{pk}.jpg",
        "price": 10.5,
        "category": category,
        "rating": {"rate": 4.0, "count": count},
    }


def make_user(username="alice", password="pw12345"):
    return User.objects.create_user(username=username, password=password)


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

class ModelTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.post = Post.objects.create(author=self.user, title="Outfit")

    def test_tag_str_pakai_hashtag(self):
        self.assertEqual(str(Tag.objects.create(name="ootd")), "#ootd")

    def test_tag_name_unik(self):
        Tag.objects.create(name="ootd")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Tag.objects.create(name="ootd")

    def test_post_str_pakai_title_atau_pk(self):
        self.assertEqual(str(self.post), "Outfit")
        kosong = Post.objects.create(author=self.user)
        self.assertEqual(str(kosong), f"Post {kosong.pk}")

    def test_image_src_pakai_url_kalau_tidak_ada_upload(self):
        post = Post.objects.create(image_url="https://example.com/a.jpg")
        self.assertEqual(post.image_src, "https://example.com/a.jpg")

    def test_detail_url_post_user(self):
        self.assertEqual(
            self.post.detail_url, reverse("inspo:user_detail", args=[self.post.pk])
        )

    def test_detail_url_produk_api(self):
        post = Post.objects.create(external_id=7)
        self.assertEqual(post.detail_url, reverse("inspo:detail", args=[7]))

    def test_bookmark_unik_per_user_dan_post(self):
        Bookmark.objects.create(user=self.user, post=self.post)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Bookmark.objects.create(user=self.user, post=self.post)

    def test_bookmark_category_unik_per_user(self):
        BookmarkCategory.objects.create(user=self.user, name="Kondangan")
        with self.assertRaises(IntegrityError), transaction.atomic():
            BookmarkCategory.objects.create(user=self.user, name="Kondangan")

    def test_bookmark_category_nama_sama_boleh_beda_user(self):
        BookmarkCategory.objects.create(user=self.user, name="Kondangan")
        lain = make_user("bob")
        BookmarkCategory.objects.create(user=lain, name="Kondangan")
        self.assertEqual(BookmarkCategory.objects.count(), 2)

    def test_hapus_post_ikut_hapus_bookmark(self):
        Bookmark.objects.create(user=self.user, post=self.post)
        self.post.delete()
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_hapus_kategori_bookmark_tidak_hapus_bookmark(self):
        cat = BookmarkCategory.objects.create(user=self.user, name="Pesta")
        bm = Bookmark.objects.create(user=self.user, post=self.post, category=cat)
        cat.delete()
        bm.refresh_from_db()
        self.assertIsNone(bm.category)

    def test_hapus_user_ikut_hapus_post(self):
        self.user.delete()
        self.assertEqual(Post.objects.count(), 0)

    def test_board_visibility(self):
        lain = make_user("bob")
        privat = Board.objects.create(owner=self.user, name="Privat")
        publik = Board.objects.create(owner=self.user, name="Publik", is_public=True)
        self.assertTrue(privat.is_visible_to(self.user))
        self.assertFalse(privat.is_visible_to(lain))
        self.assertTrue(publik.is_visible_to(lain))


# --------------------------------------------------------------------------
# Helper di views
# --------------------------------------------------------------------------

class CleanHashtagsTests(TestCase):
    def test_bersihkan_spasi_dan_huruf_besar(self):
        self.assertEqual(_clean_hashtags("ootd, Formal ,y2k"), ["ootd", "formal", "y2k"])

    def test_tanpa_duplikat(self):
        self.assertEqual(_clean_hashtags("ootd,OOTD,ootd"), ["ootd"])

    def test_maksimal_lima(self):
        self.assertEqual(len(_clean_hashtags("a,b,c,d,e,f,g")), 5)

    def test_buang_simbol_dan_item_kosong(self):
        self.assertEqual(_clean_hashtags("#ootd, ,!!,y 2k"), ["ootd", "y2k"])

    def test_string_kosong(self):
        self.assertEqual(_clean_hashtags(""), [])

    def test_dipotong_30_karakter(self):
        self.assertEqual(len(_clean_hashtags("a" * 50)[0]), 30)


# --------------------------------------------------------------------------
# Feeds
# --------------------------------------------------------------------------

class FeedsTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.url = reverse("inspo:feeds")

    @patch("inspo.views.fetch_json")
    def test_feeds_200_dan_gabung_api_dengan_post_user(self, mock_fetch):
        mock_fetch.return_value = [api_product(1, "Kaos API")]
        Post.objects.create(author=self.user, title="Post User")
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        titles = [p["title"] for p in res.context["posts"]]
        self.assertIn("Kaos API", titles)
        self.assertIn("Post User", titles)

    @patch("inspo.views.fetch_json", return_value=None)
    def test_api_gagal_set_api_error_tapi_post_user_tetap_tampil(self, _):
        Post.objects.create(author=self.user, title="Post User")
        res = self.client.get(self.url)
        self.assertTrue(res.context["api_error"])
        self.assertEqual(len(res.context["posts"]), 1)

    @patch("inspo.views.fetch_json")
    def test_post_tanpa_author_tidak_tampil_di_feed(self, mock_fetch):
        mock_fetch.return_value = []
        Post.objects.create(title="Produk impor", external_id=5)
        res = self.client.get(self.url)
        self.assertEqual(res.context["posts"], [])

    @patch("inspo.views.fetch_json")
    def test_filter_kategori_api(self, mock_fetch):
        mock_fetch.return_value = [
            api_product(1, "Kemeja", "men's clothing"),
            api_product(2, "Gaun", "women's clothing"),
        ]
        res = self.client.get(self.url, {"kategori": "Man"})
        self.assertEqual([p["title"] for p in res.context["posts"]], ["Kemeja"])

    @patch("inspo.views.fetch_json", return_value=[])
    def test_filter_kategori_post_user_lewat_tag(self, _):
        women = Tag.objects.create(name="Women")
        Post.objects.create(author=self.user, title="Rok", tag=women)
        Post.objects.create(author=self.user, title="Jaket")
        res = self.client.get(self.url, {"kategori": "Women"})
        self.assertEqual([p["title"] for p in res.context["posts"]], ["Rok"])

    @patch("inspo.views.fetch_json", return_value=[])
    def test_filter_kategori_post_user_lewat_categories_m2m(self, _):
        man = Tag.objects.create(name="Man")
        post = Post.objects.create(author=self.user, title="Blazer")
        post.categories.add(man)
        res = self.client.get(self.url, {"kategori": "Man"})
        self.assertEqual([p["title"] for p in res.context["posts"]], ["Blazer"])

    @patch("inspo.views.fetch_json", return_value=[])
    def test_kategori_tidak_valid_jatuh_ke_default(self, _):
        res = self.client.get(self.url, {"kategori": "ngawur"})
        self.assertEqual(res.context["active_category"], "Terbaru")

    @patch("inspo.views.fetch_json")
    def test_terpopuler_urut_rating_count_terbesar(self, mock_fetch):
        mock_fetch.return_value = [
            api_product(1, "Sepi", count=5),
            api_product(2, "Ramai", count=50),
        ]
        res = self.client.get(self.url, {"kategori": "Terpopuler"})
        self.assertEqual([p["title"] for p in res.context["posts"]], ["Ramai", "Sepi"])

    @patch("inspo.views.fetch_json", return_value=[])
    def test_search_filter_title(self, _):
        Post.objects.create(author=self.user, title="Blazer Kantor")
        Post.objects.create(author=self.user, title="Dress Pesta")
        res = self.client.get(self.url, {"q": "blazer"})
        self.assertEqual(len(res.context["posts"]), 1)
        self.assertEqual(res.context["posts"][0]["title"], "Blazer Kantor")

    @patch("inspo.views.fetch_json", return_value=[])
    def test_search_filter_caption(self, _):
        Post.objects.create(author=self.user, title="A", caption="cocok buat kampus")
        Post.objects.create(author=self.user, title="B", caption="buat pesta")
        res = self.client.get(self.url, {"q": "KAMPUS"})
        self.assertEqual([p["title"] for p in res.context["posts"]], ["A"])

    @patch("inspo.views.fetch_json", return_value=[])
    def test_search_tanpa_hasil(self, _):
        Post.objects.create(author=self.user, title="Blazer")
        res = self.client.get(self.url, {"q": "tidakada"})
        self.assertEqual(res.context["posts"], [])


# --------------------------------------------------------------------------
# Detail
# --------------------------------------------------------------------------

class DetailTests(TestCase):
    def setUp(self):
        self.user = make_user()

    @patch("inspo.views.fetch_json", return_value=None)
    def test_detail_404_kalau_produk_tidak_ada(self, _):
        res = self.client.get(reverse("inspo:detail", args=[999]))
        self.assertEqual(res.status_code, 404)

    @patch("inspo.views.fetch_json")
    def test_detail_produk_api_200(self, mock_fetch):
        def fake(path):
            return api_product(1) if path == "/products/1" else [api_product(1), api_product(2)]
        mock_fetch.side_effect = fake
        res = self.client.get(reverse("inspo:detail", args=[1]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["author"], "ONF")
        self.assertFalse(res.context["is_saved"])
        self.assertIsNone(res.context["bookmark_post_id"])

    @patch("inspo.views.fetch_json")
    def test_detail_is_saved_kalau_sudah_dibookmark(self, mock_fetch):
        def fake(path):
            return api_product(1) if path == "/products/1" else [api_product(1)]
        mock_fetch.side_effect = fake
        db_post = Post.objects.create(external_id=1, title="Kaos API")
        Bookmark.objects.create(user=self.user, post=db_post)
        self.client.login(username="alice", password="pw12345")
        res = self.client.get(reverse("inspo:detail", args=[1]))
        self.assertTrue(res.context["is_saved"])
        self.assertEqual(res.context["bookmark_post_id"], db_post.pk)

    @patch("inspo.views.fetch_json", return_value=[])
    def test_user_detail_200_dan_is_owner(self, _):
        post = Post.objects.create(author=self.user, title="Outfit")
        self.client.login(username="alice", password="pw12345")
        res = self.client.get(reverse("inspo:user_detail", args=[post.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context["is_owner"])

    @patch("inspo.views.fetch_json", return_value=[])
    def test_user_detail_bukan_owner(self, _):
        post = Post.objects.create(author=self.user, title="Outfit")
        make_user("bob")
        self.client.login(username="bob", password="pw12345")
        res = self.client.get(reverse("inspo:user_detail", args=[post.pk]))
        self.assertFalse(res.context["is_owner"])

    def test_user_detail_404_untuk_post_tanpa_author(self):
        post = Post.objects.create(title="Produk impor", external_id=3)
        res = self.client.get(reverse("inspo:user_detail", args=[post.pk]))
        self.assertEqual(res.status_code, 404)


# --------------------------------------------------------------------------
# Upload
# --------------------------------------------------------------------------

@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class UploadTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = make_user()
        self.url = reverse("inspo:upload")

    def login(self):
        self.client.login(username="alice", password="pw12345")

    def test_wajib_login(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 302)
        res = self.client.post(self.url, {"title": "x", "image": make_png()})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Post.objects.count(), 0)

    def test_get_form_200(self):
        self.login()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["mode"], "create")

    def test_upload_sukses(self):
        self.login()
        res = self.client.post(self.url, {
            "title": "Blazer Kantor",
            "caption": "Cocok buat magang",
            "hashtags": "ootd, Formal",
            "kategori": ["Women", "Man"],
            "image": make_png(),
        })
        post = Post.objects.get()
        self.assertRedirects(res, reverse("inspo:user_detail", args=[post.pk]))
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.title, "Blazer Kantor")
        self.assertEqual(post.caption, "Cocok buat magang")
        self.assertTrue(post.image)
        self.assertEqual(
            set(post.hashtags.values_list("name", flat=True)), {"ootd", "formal"}
        )
        self.assertEqual(
            set(post.categories.values_list("name", flat=True)), {"Women", "Man"}
        )
        self.assertEqual(post.tag.name, "Women")  # kategori utama = yang pertama

    def test_judul_wajib(self):
        self.login()
        res = self.client.post(self.url, {"title": "  ", "image": make_png()})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Judul wajib diisi.", res.context["errors"])
        self.assertEqual(Post.objects.count(), 0)

    def test_foto_wajib(self):
        self.login()
        res = self.client.post(self.url, {"title": "Outfit"})
        self.assertIn("Foto wajib diunggah.", res.context["errors"])
        self.assertEqual(Post.objects.count(), 0)

    def test_format_foto_salah(self):
        self.login()
        txt = SimpleUploadedFile("a.txt", b"halo", content_type="text/plain")
        res = self.client.post(self.url, {"title": "Outfit", "image": txt})
        self.assertIn("Foto harus berformat JPG atau PNG.", res.context["errors"])
        self.assertEqual(Post.objects.count(), 0)

    def test_file_bukan_gambar_asli(self):
        self.login()
        palsu = SimpleUploadedFile("a.png", b"bukan gambar", content_type="image/png")
        res = self.client.post(self.url, {"title": "Outfit", "image": palsu})
        self.assertIn("File yang diunggah bukan gambar yang valid.", res.context["errors"])
        self.assertEqual(Post.objects.count(), 0)

    @patch("inspo.views.MAX_IMAGE_SIZE", 10)
    def test_ukuran_foto_kebesaran(self):
        self.login()
        res = self.client.post(self.url, {"title": "Outfit", "image": make_png()})
        self.assertIn("Ukuran foto maksimal 5 MB.", res.context["errors"])
        self.assertEqual(Post.objects.count(), 0)

    def test_judul_dan_caption_dipotong(self):
        self.login()
        self.client.post(self.url, {
            "title": "t" * 150,
            "caption": "c" * 400,
            "image": make_png(),
        })
        post = Post.objects.get()
        self.assertEqual(len(post.title), 100)
        self.assertEqual(len(post.caption), 300)

    def test_kategori_tidak_valid_diabaikan(self):
        self.login()
        self.client.post(self.url, {
            "title": "Outfit",
            "kategori": ["Women", "Ngawur"],
            "image": make_png(),
        })
        post = Post.objects.get()
        self.assertEqual(list(post.categories.values_list("name", flat=True)), ["Women"])
        self.assertFalse(Tag.objects.filter(name="Ngawur").exists())


# --------------------------------------------------------------------------
# Edit
# --------------------------------------------------------------------------

@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EditTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("bob")
        self.post = Post.objects.create(author=self.user, title="Lama", caption="caption lama")
        self.url = reverse("inspo:edit", args=[self.post.pk])

    def test_wajib_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_orang_lain_dapat_404(self):
        self.client.login(username="bob", password="pw12345")
        self.assertEqual(self.client.get(self.url).status_code, 404)
        res = self.client.post(self.url, {"title": "Dibajak"})
        self.assertEqual(res.status_code, 404)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Lama")

    def test_get_form_terisi_data_lama(self):
        self.client.login(username="alice", password="pw12345")
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["mode"], "edit")
        self.assertEqual(res.context["title"], "Lama")
        self.assertEqual(res.context["caption"], "caption lama")

    def test_edit_sukses_tanpa_ganti_foto(self):
        self.client.login(username="alice", password="pw12345")
        res = self.client.post(self.url, {
            "title": "Baru",
            "caption": "caption baru",
            "hashtags": "y2k",
            "kategori": ["Man"],
        })
        self.assertRedirects(res, reverse("inspo:my_posts"))
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Baru")
        self.assertEqual(self.post.caption, "caption baru")
        self.assertEqual(self.post.tag.name, "Man")
        self.assertEqual(list(self.post.hashtags.values_list("name", flat=True)), ["y2k"])

    def test_edit_ganti_foto(self):
        self.client.login(username="alice", password="pw12345")
        self.client.post(self.url, {"title": "Baru", "image": make_png("baru.png")})
        self.post.refresh_from_db()
        self.assertTrue(self.post.image)

    def test_edit_judul_kosong_ditolak(self):
        self.client.login(username="alice", password="pw12345")
        res = self.client.post(self.url, {"title": ""})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Judul wajib diisi.", res.context["errors"])
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Lama")

    def test_edit_foto_tidak_valid_ditolak(self):
        self.client.login(username="alice", password="pw12345")
        palsu = SimpleUploadedFile("a.png", b"bukan gambar", content_type="image/png")
        res = self.client.post(self.url, {"title": "Baru", "image": palsu})
        self.assertIn("File yang diunggah bukan gambar yang valid.", res.context["errors"])


# --------------------------------------------------------------------------
# Bookmark toggle
# --------------------------------------------------------------------------

class BookmarkToggleTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.post = Post.objects.create(author=self.user, title="Outfit")
        self.url = reverse("inspo:bookmark_toggle", args=[self.post.pk])
        self.client.login(username="alice", password="pw12345")

    def test_wajib_login(self):
        self.client.logout()
        res = self.client.post(self.url, {"action": "add"})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_get_ditolak_405(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_add_bookmark(self):
        res = self.client.post(self.url, {"action": "add"})
        self.assertEqual(res.json(), {"saved": True, "category": None})
        self.assertEqual(Bookmark.objects.filter(user=self.user, post=self.post).count(), 1)

    def test_add_dua_kali_tidak_duplikat(self):
        self.client.post(self.url, {"action": "add"})
        self.client.post(self.url, {"action": "add"})
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_add_dengan_kategori_baru(self):
        res = self.client.post(self.url, {"action": "add", "new_category": "Kondangan"})
        self.assertEqual(res.json()["category"], "Kondangan")
        self.assertTrue(BookmarkCategory.objects.filter(user=self.user, name="Kondangan").exists())
        self.assertEqual(Bookmark.objects.get().category.name, "Kondangan")

    def test_kategori_baru_nama_sama_beda_huruf_tidak_dobel(self):
        BookmarkCategory.objects.create(user=self.user, name="Kondangan")
        self.client.post(self.url, {"action": "add", "new_category": "kondangan"})
        self.assertEqual(BookmarkCategory.objects.count(), 1)

    def test_add_dengan_category_id_yang_ada(self):
        cat = BookmarkCategory.objects.create(user=self.user, name="Pesta")
        res = self.client.post(self.url, {"action": "add", "category_id": str(cat.pk)})
        self.assertEqual(res.json()["category"], "Pesta")

    def test_add_lagi_memperbarui_kategori(self):
        cat = BookmarkCategory.objects.create(user=self.user, name="Pesta")
        self.client.post(self.url, {"action": "add"})
        self.client.post(self.url, {"action": "add", "category_id": str(cat.pk)})
        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertEqual(Bookmark.objects.get().category, cat)

    def test_category_id_milik_user_lain_404(self):
        bob = make_user("bob")
        cat = BookmarkCategory.objects.create(user=bob, name="Rahasia")
        res = self.client.post(self.url, {"action": "add", "category_id": str(cat.pk)})
        self.assertEqual(res.status_code, 404)
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_remove_bookmark(self):
        Bookmark.objects.create(user=self.user, post=self.post)
        res = self.client.post(self.url, {"action": "remove"})
        self.assertEqual(res.json(), {"saved": False})
        self.assertEqual(Bookmark.objects.count(), 0)

    def test_remove_tidak_menghapus_bookmark_user_lain(self):
        bob = make_user("bob")
        Bookmark.objects.create(user=bob, post=self.post)
        self.client.post(self.url, {"action": "remove"})
        self.assertEqual(Bookmark.objects.filter(user=bob).count(), 1)

    def test_action_tidak_valid_400(self):
        res = self.client.post(self.url, {"action": "x"})
        self.assertEqual(res.status_code, 400)

    def test_post_tidak_ada_404(self):
        url = reverse("inspo:bookmark_toggle", args=[99999])
        res = self.client.post(url, {"action": "add"})
        self.assertEqual(res.status_code, 404)


# --------------------------------------------------------------------------
# Halaman bookmarks & endpoint kategori
# --------------------------------------------------------------------------

class BookmarksPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("bob")
        self.url = reverse("inspo:bookmarks")
        self.p1 = Post.objects.create(author=self.user, title="Satu")
        self.p2 = Post.objects.create(author=self.user, title="Dua")
        self.cat = BookmarkCategory.objects.create(user=self.user, name="Pesta")
        self.b1 = Bookmark.objects.create(user=self.user, post=self.p1, category=self.cat)
        self.b2 = Bookmark.objects.create(user=self.user, post=self.p2)

    def login(self):
        self.client.login(username="alice", password="pw12345")

    def test_wajib_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_hanya_tampilkan_bookmark_milik_sendiri(self):
        Bookmark.objects.create(user=self.other, post=self.p1)
        self.login()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["total"], 2)
        self.assertTrue(all(b.user == self.user for b in res.context["items"]))

    def test_filter_kategori(self):
        self.login()
        res = self.client.get(self.url, {"kategori": "Pesta"})
        self.assertEqual([b.pk for b in res.context["items"]], [self.b1.pk])
        self.assertEqual(res.context["total"], 1)

    def test_sort_terbaru_dan_terlama(self):
        # paksa created_at beda supaya urutannya pasti
        Bookmark.objects.filter(pk=self.b1.pk).update(created_at="2024-01-01T00:00:00Z")
        Bookmark.objects.filter(pk=self.b2.pk).update(created_at="2024-06-01T00:00:00Z")
        self.login()
        terbaru = self.client.get(self.url, {"urut": "terbaru"})
        self.assertEqual([b.pk for b in terbaru.context["items"]], [self.b2.pk, self.b1.pk])
        terlama = self.client.get(self.url, {"urut": "terlama"})
        self.assertEqual([b.pk for b in terlama.context["items"]], [self.b1.pk, self.b2.pk])

    def test_sort_tidak_valid_jatuh_ke_terbaru(self):
        self.login()
        res = self.client.get(self.url, {"urut": "ngawur"})
        self.assertEqual(res.context["sort"], "terbaru")

    def test_kategori_hanya_milik_sendiri(self):
        BookmarkCategory.objects.create(user=self.other, name="Rahasia")
        self.login()
        res = self.client.get(self.url)
        names = [c.name for c in res.context["categories"]]
        self.assertEqual(names, ["Pesta"])

    def test_endpoint_bookmark_categories_json(self):
        BookmarkCategory.objects.create(user=self.other, name="Rahasia")
        self.login()
        res = self.client.get(reverse("inspo:bookmark_categories"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(), {"categories": [{"id": self.cat.pk, "name": "Pesta"}]}
        )

    def test_endpoint_bookmark_categories_wajib_login(self):
        res = self.client.get(reverse("inspo:bookmark_categories"))
        self.assertEqual(res.status_code, 302)
class MyPostsTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("bob")
        self.mine = Post.objects.create(author=self.user, title="Punyaku")
        Post.objects.create(author=self.other, title="Punya Bob")

    def test_wajib_login(self):
        self.assertEqual(self.client.get(reverse("inspo:my_posts")).status_code, 302)

    def test_hanya_tampilkan_post_milik_sendiri(self):
        self.client.login(username="alice", password="pw12345")
        res = self.client.get(reverse("inspo:my_posts"))
        self.assertEqual([p.title for p in res.context["posts"]], ["Punyaku"])
        self.assertEqual(res.context["total"], 1)

    def test_quick_edit_tidak_menghapus_kategori(self):
        man = Tag.objects.create(name="Man")
        self.mine.categories.add(man)
        self.client.login(username="alice", password="pw12345")
        self.client.post(reverse("inspo:quick_edit", args=[self.mine.pk]),
                         {"caption": "baru", "hashtags": "ootd"})
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.caption, "baru")
        self.assertEqual(self.mine.categories.count(), 1)   # tetap utuh

    def test_quick_edit_post_orang_lain_404(self):
        self.client.login(username="bob", password="pw12345")
        res = self.client.post(reverse("inspo:quick_edit", args=[self.mine.pk]), {"caption": "x"})
        self.assertEqual(res.status_code, 404)