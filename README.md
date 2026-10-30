# OneNightFit

## Deskripsi Aplikasi
Kebiasaan membeli pakaian secara impulsif demi mengikuti tren atau sekadar ingin tampil beda kerap berujung pada penumpukan limbah tekstil. Menjawab permasalahan ini, OneNightFit (ONF) menyediakan platform penyewaan pakaian yang praktis dan terjangkau. Tidak hanya menekan biaya pengeluaran pengguna dan mengurangi dampak buruk lingkungan, ONF juga memperpanjang siklus hidup sebuah pakaian. <br>
Disamping itu, ONF juga menyediakan *Outfit Inspo Community*, tempat bersosialisasi dan bertukar ide secara interaktif. Melalui perpaduan antara *sustainable fashion* dan dukungan komunitas, ONF mengajak masyarakat untuk tampil modis secara lebih bijak dan berkelanjutan.

## PBP E - Kelompok 7

Anggota Kelompok:

- Fahira Ryhanabila (2506623660)
- Kayla Alifah Khairunnisa (2506611931)
- Khadijah Asy Syakira (2506610595)
- Zahra Nayla Azfa (2506534163)

## Daftar Modul

| Nama Modul | Deskripsi Modul | CRUD | Anggota Kelompok |
|---|---|---|---|
| Authentication and User Dashboard |Mengelola akun dan informasi pribadi pengguna dalam website. Fitur meliputi Register, Login, Logout, View Profile, Edit Profile,  Activity History, dan Delete Account.| **Create:** Membuat akun/register.<br>**Read:** Melihat profil dan riwayat aktivitas.<br>**Update:** Mengedit profil dan password.<br>**Delete:** Menghapus akun.| Kayla Alifah Khairunnisa |
| Product Catalog | Mengelola daftar pakaian yang tersedia untuk disewa oleh pembeli.| **Create:** Menambahkan *item* baru ke katalog.<br>**Read:** Menelusuri daftar baju dengan filter pencarian.<br>**Update:** Mengubah deskripsi atau harga sewa *item*.<br>**Delete:** Menghapus *item* dari katalog.| Khadijah Asy Syakira |
| Product Cart | Mengelola keranjang penyimpanan produk yang akan disewa oleh pengguna sebelum melakukan pemesanan. | **Create:** Menambahkan produk ke keranjang, membuat pesanan sewa (*booking*).<br>**Read:** Menampilkan daftar produk dalam keranjang.<br>**Update:** Mengubah lama hari peminjaman produk.<br>**Delete:** Menghapus produk dari keranjang. | Zahra Nayla Azfa |
| Inspo | Wadah bagi pengguna untuk membagikan foto gaya busana mereka, termasuk outfit yang menggunakan baju sewaan ONF. Fitur meliputi Upload, Comment, Like, Share Bookmark, dan Search. | **Create:** Membuat unggahan foto *outfit* baru, membuat kategori bookmark baru, dan menyukai postingan.<br>**Read:** Menampilkan lini masa (*feed*) kiriman komunitas, pencarian, filter kategori, detail postingan, serta menampilkan halaman *My Post, Like,* dan *Bookmarks*.<br>**Update:** Mengedit postingan sendiri yang meliputi judul, *caption, hashtag*, kategori, foto, dan produk .<br>**Delete:** Menghapus kiriman milik sendiri, batal *like*, dan hapus *bookmark*. | Fahira Ryhanabila |

## API

https://fakeapi.platzi.com/en/about/introduction/

## User Roles

- **Guest:** melihat katalog baju dan *inspo board*.
- **User:** semua akses *Guest* dengan tambahan kelola keranjang, checkout, dan upload *inspo*.
- **Seller:** semua akses *User* dengan tambahan membuat katalog produk untuk dijual.
- **Admin:** kelola web, app, dan verifikasi.

## Link Figma

https://www.figma.com/design/K646xfiXLzAk07bq81ZwJx/OneNightFit?node-id=0-1&t=YFX1KXFEy7eudGNm-1

## Cara Menjalankan Proyek Secara Lokal
1. Unduh salinan repositori ini ke perangkat Anda, kemudian pindah ke direktori proyek:
    ```
    git clone https://github.com/OneNightFit/OneNightFit.git
    cd myportofolio
    ```
2. Siapkan lingkungan virtual (*virtual environment*) agar dependensi proyek tidak bercampur dengan instalasi Python global di komputer Anda:
    ```
    python -m venv env
    env\Scripts\activate    # Windows
    source env/bin/activate # macOS/Linux
    ```
3. Pasang seluruh pustaka (*library*) yang dibutuhkan proyek melalui berkas `requirements.txt`:
    ```
    pip install -r requirements.txt
    ```
4. Terapkan migrasi basis data bawaan Django agar struktur tabel tersinkronisasi:
    ```
    python manage.py migrate
    ```
5. Impor data awal ke dalam basis data
    ## TODO: Masukin impor modul kalian disini
    ```
    python manage.py import_products
    python manage.py import_catalog
    ```
6. Jalankan server:
    ```
    python manage.py runserver
    ```
7. Akses proyek melalui browser dengan membuka alamat `http://localhost:8000`


## Modul Authentication and User
Konten pada modul Authentication & User meliputi:

- **Registrasi, Login, dan Logout:** Pengguna membuat akun dan memilih peran sebagai Buyer atau Seller. Peran disimpan di profil pengguna (`profile.is_buyer` dan `profile.is_seller`) dan menentukan menu serta tab yang tampil. Pengunjung yang belum login diarahkan ke halaman login saat membuka halaman yang dilindungi.
- **Profil Pengguna:** Halaman profil menampilkan avatar inisial, lencana peran (Buyer atau Seller), nama pengguna, dan email. Navigasi tab pada profil menyesuaikan peran: Buyer memiliki tab Profile, Activity, Rentals, dan Edit Profile, sedangkan Seller memiliki tab Profile, Shop Report, dan Edit Profile.
- **Edit Profil:** Pengguna dapat mengubah data profilnya sendiri. Pembatasan akses dilakukan di sisi server, sehingga pengguna hanya dapat mengubah profil miliknya.
- **Activity (Buyer):** Mengumpulkan aktivitas pengguna dari modul lain dalam tiga tab dengan jumlah item pada setiap tab.
  - **Wishlist:** produk katalog yang disimpan pengguna (hanya untuk Buyer). Tombol Remove menghapus produk dari wishlist tanpa memuat ulang halaman, dan mengklik kartu membuka modal detail produk.
  - **Like:** postingan Inspo yang disukai pengguna, memakai tampilan grid yang sama dengan halaman Likes pada modul Inspo.
  - **Bookmark:** postingan Inspo yang disimpan, lengkap dengan filter kategori, pengurutan terbaru atau terlama, dan hapus langsung. Tampilannya memakai komponen yang sama dengan halaman Bookmarks pada modul Inspo.
- **Rentals (Buyer):** Menampilkan riwayat sewa milik Buyer beserta statusnya (menunggu persetujuan, sedang disewa, dan dikembalikan).
- **Shop Report (Seller):** Ringkasan toko berisi jumlah produk yang disewakan, sewa aktif, total sewa, dan total pendapatan, ditambah grafik pendapatan enam bulan terakhir. Daftar produk Seller dapat disaring menjadi *Available*, *Pending*, dan *Rented*. Status ini dihitung dari data pesanan, bukan disimpan sebagai kolom pada produk, sehingga tidak bisa tidak sinkron.
- **Alur Pesanan Sewa:** Checkout oleh Buyer membuat pesanan berstatus *pending* dan menahan stok produk. Seller dapat menyetujui (menjadi *renting*) atau menolak pesanan, lalu menandai *returned* ketika barang dikembalikan. Harga dikunci saat checkout supaya pendapatan tidak berubah ketika harga produk diedit.
- **Penghubung Antar Modul (`integrations.py`):** Hanya file ini yang mengetahui nama model dan field milik modul lain (Catalog, Inspo, dan Cart). Arah ketergantungan satu arah: Authentication membaca modul lain, sedangkan modul lain tidak meng-import Authentication. Jika modul lain belum digabung atau modelnya tidak ditemukan, halaman tampil kosong dan tidak error.
- **Autentikasi dan Hak Akses:** Halaman Profile, Activity, Rentals, Shop Report, dan Edit Profile hanya dapat diakses pengguna yang login. Aksi Seller (approve, reject, returned) memeriksa kepemilikan di sisi server, sehingga Seller lain mendapat respons 404 meskipun mengetahui alamatnya. Pembatasan dilakukan di sisi server, bukan hanya dengan menyembunyikan tombol.
- **Keamanan Input:** Seluruh aksi yang mengubah data memakai request POST dengan token CSRF. Teks yang disisipkan lewat JavaScript memakai `textContent` untuk mencegah XSS, dan alamat tujuan `next` pada form divalidasi agar tidak mengarah ke situs lain.

### **AI Disclosure Modul Inspo**
### **1. Alat AI yang digunakan**

Claude (Model Bahasa / AI Assistant)


### **2. Ruang Lingkup Bantuan AI**

- **Struktur Django:** Menjelaskan pemisahan tanggung jawab antar app, penggunaan `views.py`, `urls.py`, template, partial (`{% include %}`), dan static files pada modul authentication.
- **Integrasi Antar Modul:** Membantu merancang `integrations.py` agar modul Authentication membaca data Catalog dan Inspo tanpa saling bergantung, termasuk fungsi pengambilan data Wishlist, Like, Bookmark, dan data Shop Report.
- **Model dan Database:** Membantu merancang model pesanan sewa (Order dan OrderItem atau Rental) berikut status, penguncian harga, dan perhitungan stok, serta cara membuat migrasi.
- **Frontend:** Memberikan saran penyusunan HTML, CSS, dan JavaScript untuk tab Activity, filter Shop Report, penghapusan wishlist tanpa reload, dan pembukaan modal detail produk dari kartu wishlist.
- **Debugging:** Membantu membaca pesan error (misalnya `TemplateSyntaxError` akibat tag `elif` atau `endblock` yang tertinggal, dan peringatan import pada VS Code) lalu menelusuri penyebabnya.

### **3. Strategi Prompting**

- **Contextual Prompting:** Menyertakan potongan kode, isi file (`views.py`, `integrations.py`, template), serta screenshot tampilan aplikasi agar bantuan sesuai dengan kondisi proyek.
- **Iterative and Conversational Prompting:** Mengajukan pertanyaan bertahap, misalnya dari memisahkan komponen bookmark, lalu menyambungkannya ke tab Activity, kemudian menyesuaikan dengan aturan `integrations.py`.
- **Problem-Based Questioning:** Menempelkan pesan error lengkap atau screenshot halaman error untuk memperoleh penyebab yang spesifik.
- **Verification Prompting:** Meminta cara memeriksa hasil, misalnya daftar skenario uji dengan dua akun (Buyer dan Seller) untuk alur pending, approve, dan returned.
- **UI Evaluation Prompting:** Mengirim tampilan aktual halaman untuk memperoleh masukan perbedaan antara desain dan implementasi, misalnya tab pill yang belum ter-style.
- **Conceptual Follow-up:** Menanyakan alasan di balik keputusan teknis, misalnya mengapa status renting tidak disimpan di model Product, dan apakah perlu model khusus untuk pesanan sewa.

### **4. Log Chat AI**

Link = https://claude.ai/share/bd7e1475-315b-42a3-9e1a-b8221bff2673

### **5. Evaluasi Kritis terhadap Penggunaan AI**

AI digunakan sebagai pendukung pemahaman dan pembuatan draf kode untuk modul Authentication dan User. Saran AI tidak langsung dipakai apa adanya. AI tidak sepenuhnya memahami lingkungan proyek ini sehingga banyak yang harus dipertimbangkan untuk disesuaikan kembali. Contohnya, AI sempat menyarankan agar view Activity mengimpor model Inspo secara langsung, lalu saran itu ditinjau ulang dan diubah agar mengikuti aturan `integrations.py` yang menyatakan hanya file tersebut yang boleh mengetahui nama model modul lain. Banyak nama model dan field pada draf AI berupa asumsi (misalnya `OrderItem`, `Rental`, atau nama URL), sehingga semuanya dicocokkan dengan kode proyek yang sebenarnya sebelum dipakai. Implementasi, pengujian, verifikasi hasil, dan pengambilan keputusan akhir tetap dilakukan oleh saya. Dengan demikian, AI dimanfaatkan untuk membantu proses belajar dan mencari solusi atas permasalahan yang dihadapi, sedangkan penyusunan dan hasil akhir modul tetap saya kembangkan dan tentukan sendiri.



## Modul Product Catalog



## Modul Product Cart



## Modul Inspo

Konten pada modul Inspo meliputi:
- **Feed Inspo**: Menampilkan kumpulan item dalam tata letak kolom yang menyesuaikan lebar layar. Isi feed berasal dari dua sumber: produk dari Fake Store API dan postingan outfit yang diunggah pengguna. Dilengkapi pill kategori untuk menyaring item.
- **Pencarian**: Kolom pencarian pada header feed mencari item berdasarkan kata pada judul item, dan hasilnya tetap mengikuti kategori yang sedang aktif.
- **Banner Iklan**: Banner *"New Arrival"* di bagian atas feed berisi konten dummy. Tombol pada banner mengarahkan pengguna ke halaman katalog produk.
- **Detail Postingan**: Menampilkan foto, deskripsi, jumlah like, komentar, dan button bookmarks (save). Jika postingan menautkan produk ONF, tersedia tombol yang mengarahkan ke halaman detail produk di katalog. Item dapat dimasukkan ke wishlist atau keranjang melalui modul lain.
- **Like**: Pengguna yang sudah login dapat menyukai atau membatalkan like dari menu pada kartu postingan. Item yang disukai disimpan di profil pengguna sebagai postingan yang disukai.
- **Bookmarks**: Saat ikon bookmark diklik, pengguna dapat memilih kategori bookmark yang sudah ada atau membuat kategori baru, lalu postingan tersimpan. Halaman Bookmarks menampilkan simpanan dalam grid responsif, dapat disaring per kategori dan diurutkan dari yang terbaru atau terlama disimpan. Menghapus bookmark berlaku langsung (kartu memudar dan hilang), disertai toast "Urungkan" selama 5 detik. Bookmark hanya dapat dilihat oleh pemiliknya.
- **Komentar dan Share**: Antarmuka komentar (menulis, membalas, dan menyukai komentar) sudah tersedia, tetapi datanya masih berupa dummy dan tidak tersimpan. Postingan dapat dibagikan lewat tautan menggunakan fitur share bawaan browser atau salin tautan.
- **Upload Postingan**: Pengguna mengunggah outfit lewat halaman Upload yang terletak pada profil dengan pratinjau foto sebelum dikirim. Foto dan judul wajib diisi. Caption (maks. 300 karakter), hashtag (maks. 5), kategori, dan tag produk bersifat opsional. Foto divalidasi di sisi server (hanya JPG atau PNG, maks. 5 MB, dan harus berupa gambar yang valid).
- **Tag Produk ONF**: Saat mengunggah atau mengedit postingan, pengguna dapat memilih produk sewaan dari katalog. Produk yang dipilih tampil sebagai kartu berisi foto, nama, dan harga, dan dapat dihapus kembali.
- **My Post**: Menampilkan postingan milik pengguna sendiri dengan akses menuju halaman upload, edit, dan hapus, yang terletak di bagian profil pengguna
- **Edit dan Hapus Postingan**: Pemilik postingan dapat mengubah judul, caption, hashtag, kategori, foto, dan produk yang ditautkan, serta menghapus postingan miliknya. Postingan milik pengguna lain tidak dapat diubah meskipun alamatnya diketahui, karena kepemilikan diperiksa di sisi server.
- **Data dari API**: Produk diambil dari Fake Store API dan disimpan ke basis data lewat perintah `python manage.py import_products`. Perintah ini dapat dijalankan berulang karena memperbarui data yang sama, bukan menggandakannya, dan dijalankan di terminal PWS agar data juga tampil di PWS.
- **Autentikasi & Hak Akses**: Halaman Upload, Edit, Bookmarks, dan Likes hanya dapat diakses pengguna yang login (pengunjung diarahkan ke halaman login). Feed dan detail postingan dapat dibaca tanpa login. Pembatasan akses dilakukan di sisi server, bukan hanya dengan menyembunyikan tombol.
- **Keamanan Input**: Seluruh aksi yang mengubah data memakai request `POST` dengan token CSRF. Teks yang disisipkan lewat JavaScript memakai `textContent` untuk mencegah XSS, dan hashtag dibersihkan dari karakter selain huruf, angka, dan garis bawah.
- **Responsive Layout**: Tata letak menyesuaikan tampilan desktop dan mobile menggunakan CSS Grid, Flexbox, dan `@media` query

### **AI Disclosure Modul Inspo**
### **1. Alat AI yang digunakan**
* Claude (Model Bahasa / AI Assistant)

### **2. Ruang Lingkup Bantuan AI**
* **Alur Git dalam Kolaborasi Tim**: Membantu dalam memahami alur branch, Pull Request, merge conflict, serta cara mengetahui workflow GitHub Actions untuk deploy ke PWS.
* **Struktur Django**: Menjelaskan perbedaan antara project dan app, penggunaan `urls.py`, `views.py`, template, dan static files, serta penyusunan app `inspo`.
* **Model & Database**: Membantu merancang model `Post`, `Tag`, `Bookmark`, dan `Bookmarkcategory`, termasuk didalamnya relasi `ForeignKey` ke model `Product` dari modul Catalog dan cara membuat migrasi.
* **Integrasi API**: Menjelaskan cara pengambilan *(fetch)* data dari Fake Store API dan menyimpannya lewat management command `import_products`.
* **Frontend**: Memberikan saran dalam penyusunan struktur HTML, CSS, dan javaScript untuk halaman feed, detail postingan, like, dan Bookmarks. Bantuan juga mencakup penjelasan alur interaksi antarkomponen, serta evaluasi dan perbaikan kode berdasarkan kebutuhan fungsional modul
* **UI/UX:** Memberi masukan terhadap desain halaman yang sudah dibuat (tombol, state kosong, toast, dan kartu postingan).
* **Dokumentasi:** Membantu menyusun deskripsi modul, klasifikasi CRUD, panduan menjalankan modul, dan dokumen AI Disclosure ini.

### ***3. Strategi *Prompting***
* **Contextual Prompting:** Menyertakan potongan kode, struktur folder, screenshot desain Figma dan tampilan aplikasi, serta arahan asdos agar bantuan sesuai dengan kondisi proyek.
* **Iterative & Conversational Prompting:** Mengajukan pertanyaan bertahap berdasarkan hasil perintah di terminal, misalnya `git status`, `git log`, dan keluaran `runserver`.
* **Problem-Based Questioning:** Mengajukan masalah teknis spesifik dengan menempelkan pesan error lengkap.
* **Verification Prompting:** Meminta cara memeriksa hasil, misalnya perintah `Select-String` untuk memastikan baris tertentu ada, `makemigrations --check`, dan skenario uji manual per fitur.
* **UI Evaluation Prompting:** Mengirim desain dan tampilan aktual halaman untuk memperoleh masukan perbedaan antara desain dan implementasi.
* **Conceptual Follow-up:** Menanyakan alasan di balik keputusan teknis, misalnya kapan memakai app terpisah, mengapa branch dibuat dari `dev`, dan perbedaan Bookmark dengan Like.

### **4. Log Chat AI**
Link = https://claude.ai/share/2f302fe8-4f89-4b3a-9e18-bf87226e812b

### **5. Evaluasi Kritis terhadap Penggunaan AI**
AI digunakan sebagai pendukung pemahaman dan pembuatan draf kode untuk modul Inspo. Beberapa saran juga saya sesuaikan dengan arahan asdos, misalnya data feed yang harus berasal dari API. Form Upload dan Edit pada versi akhir saya tulis sendiri dengan pemrosesan yang berbeda dari draf awal. Implementasi, pengujian, verifikasi hasil, review lewat Pull Request, dan pengambilan keputusan akhir tetap dilakukan oleh saya. Dengan demikian, AI berperan sebagai pendukung proses pembelajaran dan pemecahan masalah, sedangkan hasil akhir modul tetap merupakan hasil pengembangan dan keputusan saya.

