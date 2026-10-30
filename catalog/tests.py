from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from decimal import Decimal
from unittest.mock import patch

from catalog.models import Product, ProductRating
from catalog.forms import ProductForm

# ================================
# 1. MODELS TEST
# ================================
class ProductModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testbuyer', password='password123')
        self.seller = User.objects.create_user(username='testseller', password='password123')
        
        self.product = Product.objects.create(
            name="Classic T-Shirt",
            seller=self.seller,
            description="A comfortable cotton shirt.",
            price=Decimal('150.000'),
            category="men_clothing",
            size="L"
        )

    def test_product_str(self):
        """Test representasi string dari model Product"""
        self.assertEqual(str(self.product), "Classic T-Shirt")

    def test_product_rating_properties(self):
        """Test properti average_rating dan rating_count"""
        # Awalnya belum ada rating, harus mengembalikan 0.0 dan 0
        self.assertEqual(self.product.average_rating, 0.0)
        self.assertEqual(self.product.rating_count, 0)

        # Tambahkan rating
        ProductRating.objects.create(product=self.product, user=self.user, score=4)
        self.assertEqual(self.product.rating_count, 1)
        self.assertEqual(self.product.average_rating, 4.0)

    def test_is_wishlisted_by(self):
        """Test fungsi is_wishlisted_by untuk user terautentikasi dan tamu"""
        # User belum menambahkan ke wishlist
        self.assertFalse(self.product.is_wishlisted_by(self.user))
        
        # Tambahkan ke wishlist
        self.product.wishlisted_by.add(self.user)
        self.assertTrue(self.product.is_wishlisted_by(self.user))

# ================================
# 2. FORMS TEST
# ================================
class ProductFormTest(TestCase):
    def test_product_form_valid(self):
        """Test form dengan input data yang benar"""
        form_data = {
            'name': 'Kemeja Flanel',
            'category': 'men_clothing',
            'description': 'Kemeja flanel tebal nyaman dipakai',
            'price': '200.000'
        }
        form = ProductForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_product_form_invalid(self):
        """Test form gagal jika ada field wajib yang kosong (misal harga hilang)"""
        form_data = {
            'name': 'Kemeja Flanel',
            'category': 'men_clothing',
            'description': 'Kemeja flanel',
        }
        form = ProductForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

# ================================
# 3. VIEWS TEST
# ================================
class ProductViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Buat dummy users
        self.buyer_user = User.objects.create_user(username='buyer', password='123')
        self.seller_user1 = User.objects.create_user(username='seller1', password='123')
        self.seller_user2 = User.objects.create_user(username='seller2', password='123')

        # Buat dummy product
        self.product = Product.objects.create(
            name="Test Jacket",
            seller=self.seller_user1,
            description="Testing jacket views",
            price=Decimal('500.000'),
            category="men_clothing"
        )

    def test_catalog_list_view(self):
        """Test list view dapat merender semua produk dan menangani getlist category"""
        response = self.client.get(reverse('catalog:catalog_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Jacket")
        
        # Uji logic filtering menggunakan query params
        response_filtered = self.client.get(reverse('catalog:catalog_list') + '?category=men_clothing')
        self.assertContains(response_filtered, "Test Jacket")
        
        response_empty = self.client.get(reverse('catalog:catalog_list') + '?category=electronics')
        self.assertNotContains(response_empty, "Test Jacket")

    def test_product_detail_view(self):
        """Test detail produk berhasil dirender atau mengeluarkan error 404"""
        response = self.client.get(reverse('catalog:product_detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['product'].name, "Test Jacket")

    @patch('catalog.views.is_seller', return_value=True)
    def test_create_product_success(self, mock_is_seller):
        """Test seller dapat membuat produk baru melalui POST request"""
        self.client.force_login(self.seller_user1)
        response = self.client.post(reverse('catalog:create_product'), {
            'name': 'New Trouser',
            'category': 'men_clothing',
            'description': 'A new pair of trousers.',
            'price': '300.000'
        })
        # Sukses membuat produk harus mengembalikan status code 302 (redirect ke catalog_list)
        self.assertRedirects(response, reverse('catalog:catalog_list'))
        self.assertEqual(Product.objects.count(), 2)

    @patch('catalog.views.is_seller', return_value=False)
    def test_create_product_forbidden(self, mock_is_seller):
        """Test user biasa (bukan seller) yang mencoba create_product di-redirect kembali ke list"""
        self.client.force_login(self.buyer_user)
        response = self.client.post(reverse('catalog:create_product'), {})
        self.assertRedirects(response, reverse('catalog:catalog_list'))

    @patch('catalog.views.is_seller', return_value=True)
    def test_edit_product_success(self, mock_is_seller):
        """Test seller mengedit produk miliknya sendiri"""
        self.client.force_login(self.seller_user1)
        response = self.client.post(reverse('catalog:edit_product', args=[self.product.id]), {
            'name': 'Updated Jacket',
            'category': 'men_clothing',
            'description': 'Updated description',
            'price': '550.000'
        })
        self.assertRedirects(response, reverse('catalog:catalog_list'))
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Jacket')

    @patch('catalog.views.is_seller', return_value=True)
    def test_edit_product_permission_denied(self, mock_is_seller):
        """Test seller lain tidak dapat mengedit produk yang bukan miliknya (raise 403)"""
        self.client.force_login(self.seller_user2)
        response = self.client.post(reverse('catalog:edit_product', args=[self.product.id]), {})
        self.assertEqual(response.status_code, 403)

    @patch('catalog.views.is_seller', return_value=True)
    def test_delete_product(self, mock_is_seller):
        """Test seller dapat menghapus produknya"""
        self.client.force_login(self.seller_user1)
        response = self.client.post(reverse('catalog:delete_product', args=[self.product.id]))
        self.assertRedirects(response, reverse('catalog:catalog_list'))
        self.assertEqual(Product.objects.count(), 0)

    def test_toggle_wishlist(self):
        """Test menambah dan menghapus wishlist"""
        self.client.force_login(self.buyer_user)
        
        # Tambah ke wishlist
        response = self.client.post(reverse('catalog:toggle_wishlist', args=[self.product.id]))
        self.assertRedirects(response, reverse('catalog:catalog_list'))
        self.assertTrue(self.buyer_user in self.product.wishlisted_by.all())
        
        # Hapus dari wishlist (Toggle off)
        self.client.post(reverse('catalog:toggle_wishlist', args=[self.product.id]))
        self.assertFalse(self.buyer_user in self.product.wishlisted_by.all())

    def test_add_to_cart_redirect(self):
        """Test views add_to_cart mengarahkan kembali ke halaman awal untuk user yang login"""
        self.client.force_login(self.buyer_user)
        response = self.client.get(reverse('catalog:add_to_cart', args=[self.product.id]))
        self.assertRedirects(response, reverse('catalog:catalog_list'))