(function () {
    const modal = document.getElementById('product-detail-modal');
    if (!modal) return;

    const DUMMY_ID = '00000000-0000-0000-0000-000000000000';
    const IS_SELLER = modal.dataset.isSeller === 'true';
    const cache = new Map();

    const urlFor = (tpl, id) => tpl.replace(DUMMY_ID, id);
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
        $('#detail-cart').hidden = IS_SELLER;
    }

    async function openProductDetail(id) {
        try {
            let p = cache.get(id);
            if (!p) {
                const res = await fetch(urlFor(modal.dataset.detailUrl, id), {
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
            const res = await fetch(urlFor(modal.dataset.cartUrl, id), {
                method: 'POST',
                headers: { 'X-CSRFToken': modal.dataset.csrf },
            });
            if (res.status === 401) { window.location.href = '/login/'; return; }
            const result = await res.json().catch(() => ({}));
            notify(res.ok ? 'Berhasil' : 'Gagal', result.message || '', res.ok ? 'success' : 'error');
        } catch (err) {
            console.error(err);
            notify('Error', 'Tidak dapat terhubung ke server.', 'error');
        }
    }

    async function toggleWishlist(id, button) {
        try {
            const res = await fetch(urlFor(modal.dataset.wishlistUrl, id), {
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
            if (res.status === 401) { window.location.href = '/login/'; return; }
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
        if (button.dataset.action === 'cart') addToCart(id);
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
