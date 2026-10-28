(() => {
  const dlg = document.getElementById('bm-picker');
  if (!dlg) return;

  const list = dlg.querySelector('.bmp-list');
  const form = dlg.querySelector('.bmp-new');
  const input = form.querySelector('input');
  const err = dlg.querySelector('.bmp-error');
  const csrf = dlg.querySelector('[name=csrfmiddlewaretoken]').value;
  let ctx = null;   // { url, onSaved }

  function render(categories) {
    list.replaceChildren();
    if (!categories.length) {
      const p = document.createElement('p');
      p.className = 'bmp-empty';
      p.textContent = 'Belum ada kategori. Buat yang pertama di bawah.';
      list.append(p);
      return;
    }
    categories.forEach(c => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'bmp-item';
      b.dataset.id = c.id;
      b.textContent = c.name;          // textContent = aman dari XSS
      list.append(b);
    });
  }

  async function save(extra) {
    err.textContent = '';
    try {
      const res = await fetch(ctx.url, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf },
        body: new URLSearchParams({ action: 'add', ...extra }),
      });
      if (res.redirected) { location.href = res.url; return; }   // belum login
      if (!res.ok) throw new Error('failed');
      const data = await res.json();
      dlg.close();
      if (ctx.onSaved) ctx.onSaved(data);
    } catch (_) {
      err.textContent = 'Gagal menyimpan, coba lagi.';
    }
  }

  window.openBookmarkPicker = async function (url, onSaved) {
    ctx = { url, onSaved };
    err.textContent = '';
    input.value = '';
    list.replaceChildren();
    dlg.showModal();
    try {
      const res = await fetch(dlg.dataset.categoriesUrl, { headers: { Accept: 'application/json' } });
      if (res.redirected) { location.href = res.url; return; }
      render((await res.json()).categories);
    } catch (_) {
      err.textContent = 'Gagal memuat kategori.';
    }
  };

  list.addEventListener('click', e => {
    const b = e.target.closest('.bmp-item');
    if (b) save({ category_id: b.dataset.id });
  });

  form.addEventListener('submit', e => {
    e.preventDefault();
    const name = input.value.trim();
    if (!name) { err.textContent = 'Nama kategori tidak boleh kosong.'; return; }
    save({ new_category: name });
  });

  dlg.querySelector('.bmp-close').addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });   // klik area gelap
})();