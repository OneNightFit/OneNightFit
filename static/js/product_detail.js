(function () {
    const modal = document.getElementById('product-detail-modal');
    if (!modal) return;

    const IS_SELLER = modal.dataset.isSeller === 'true';
    const cache = new Map();

    const detailUrlFor = id => modal.dataset.detailUrl.replace('00000000-0000-0000-0000-000000000000', id);
    const $ = sel => modal.querySelector(sel);

    function notify(title, message, type) {
        if (typeof showToast === 'function') showToast(title, message, type);
        else alert(`${title}: ${message}`);
    }

    function fill(p) {
        $('#detail-category').textContent = p.category_display;
        $('#product-detail-title').textContent = p.name;
        $('#detail-desc').textContent = p.description;
        $('#detail-price').textContent = `Price: Rp ${p.price}`;
        $('#detail-rating').textContent = `Rating: ${p.average_rating}`;
        $('#detail-reviews').textContent = `Rated by ${p.rating_count} people`;
        $('#detail-seller').textContent = `Store: ${p.seller}`;
        $('#detail-meta').textContent = `Ukuran: ${p.size_display}`;

        const img = $('#detail-image');
        if (p.image) { img.src = p.image; img.alt = p.name; img.hidden = false; }
        else { img.removeAttribute('src'); img.hidden = true; }

        const wl = $('#detail-wishlist');
        wl.classList.toggle('is-wishlisted', !!p.is_wishlisted);
        wl.textContent = p.is_wishlisted ? 'Remove from wishlist' : 'Add to wishlist';
        wl.hidden = IS_SELLER;
        const cartButton = $('#detail-cart');
        cartButton.hidden = IS_SELLER;
        cartButton.classList.toggle('button-primary', !p.is_in_cart);
        cartButton.classList.toggle('button-tertiary', !!p.is_in_cart);
        cartButton.textContent = p.is_in_cart ? 'Remove from cart' : cartButton.dataset.defaultLabel;
        $('#detail-cart-status').hidden = !p.is_in_cart;
    }

    async function openProductDetail(id) {
        try {
            let p = cache.get(id);
            if (!p) {
                const res = await fetch(detailUrlFor(id), {
                    headers: { 'Accept': 'application/json' },
                });
                if (!res.ok) throw new Error('not found');
                p = (await res.json()).fields;
                cache.set(id, p);
            }
            modal.dataset.id = id;
            fill(p);
            modal.showPopover();
        } catch (err) {
            console.error(err);
            notify('Gagal', 'Produk tidak ditemukan.', 'error');
        }
    }

    async function addToCart(id) {
        try {
            const res = await fetch(modal.dataset.cartUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': modal.dataset.csrf,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                },
                body: new URLSearchParams({ product_id: id }),
            });
            const result = await res.json().catch(() => ({}));
            if (res.status === 401) {
                notify('Gagal menambahkan produk', result.error || result.message || 'Harap login terlebih dahulu.', 'error');
                const loginUrl = modal.dataset.loginUrl || '/login/';
                window.setTimeout(() => { window.location.href = loginUrl; }, 3200);
                return;
            }
            const message = res.ok
                ? (result.message || 'Produk berhasil ditambahkan ke keranjang.')
                : (result.error || result.message || `Terjadi kesalahan saat menambahkan produk (status ${res.status}).`);
            if (res.ok) {
                const button = $('#detail-cart');
                button.classList.remove('button-primary');
                button.classList.add('button-tertiary');
                button.textContent = 'Remove from cart';
                $('#detail-cart-status').hidden = false;
                const product = cache.get(id);
                if (product) product.is_in_cart = true;
                document.dispatchEvent(new CustomEvent('product:changed', { detail: { id } }));
            }
            notify(res.ok ? 'Berhasil' : 'Gagal menambahkan produk', message, res.ok ? 'success' : 'error');
        } catch (err) {
            console.error(err);
            notify('Gagal menambahkan produk', `Tidak dapat terhubung ke server: ${err.message}`, 'error');
        }
    }

    async function toggleWishlist(id, button) {
        try {
            const res = await fetch(modal.dataset.wishlistUrl.replace('00000000-0000-0000-0000-000000000000', id), {
                method: 'POST',
                headers: {
                    'X-CSRFToken': modal.dataset.csrf,
                    'Accept': 'application/json',
                },
            });
            if (res.redirected && res.url.includes('/login')) {
                window.location.href = res.url;
                return;
            }
            if (res.status === 401) {
                window.location.href = modal.dataset.loginUrl || '/login/';
                return;
            }
            const result = await res.json().catch(() => ({}));
            if (!res.ok) return notify('Gagal', result.message || 'Gagal memperbarui wishlist.', 'error');

            const on = !!result.is_wishlisted;
            button.classList.toggle('is-wishlisted', on);
            button.textContent = on ? 'Remove from wishlist' : 'Add to wishlist';
            const cached = cache.get(id);
            if (cached) cached.is_wishlisted = on;
            document.dispatchEvent(new CustomEvent('product:changed', { detail: { id } }));
        } catch (err) {
            console.error(err);
            notify('Error', 'Tidak dapat terhubung ke server.', 'error');
        }
    }

    // Klik tombol di dalam modal
    modal.addEventListener('click', event => {
        const button = event.target.closest('button[data-action]');
        if (!button) return;
        const id = modal.dataset.id;
        if (button.dataset.action === 'cart') {
            if (button.textContent === 'Remove from cart') {
                notify('Hapus produk dari halaman Cart', "Klik tombol 'remove' di halaman cart untuk menghapus produk dari cart", 'info');
                window.setTimeout(() => { window.location.href = modal.dataset.cartPageUrl; }, 3200);
            } else {
                addToCart(id);
            }
        }
        if (button.dataset.action === 'wishlist') toggleWishlist(id, button);
    });

    // Trigger global: elemen apa pun dengan data-product-detail="<id>"
    document.addEventListener('click', event => {
        if (event.target.closest('#product-detail-modal')) return;
        if (event.target.closest('button[data-action]')) return;
        const trigger = event.target.closest('[data-product-detail]');
        if (!trigger) return;
        event.preventDefault();
        openProductDetail(trigger.dataset.productDetail);
    });

    window.openProductDetail = openProductDetail;
})();
