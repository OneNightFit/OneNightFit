(() => {
  const $ = id => document.getElementById(id);
  const grid = $('grid');
  if (!grid) return;

  const empty = $('empty'), totalEl = $('total'), uploadTop = $('upload-top');
  const editModal = $('edit-modal'), editForm = $('edit-form');
  const delModal = $('delete-modal'), delForm = $('delete-form');
  const MAX_CAPTION = 50, MAX_TAGS = 5;
  let currentCard = null;

  /* ---------- Toast ---------- */
  let toastTimer;
  function toast(msg) {
    const t = $('toast');
    t.textContent = msg;
    t.classList.add('is-show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('is-show'), 2500);
  }

  /* ---------- Kirim form lewat fetch ---------- */
  async function send(form) {
    const res = await fetch(form.action, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: new FormData(form),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  /* ---------- Counter caption ---------- */
  const cap = $('edit-caption'), capCount = $('cap-count'), capBox = $('cap-counter');
  function updateCap() {
    capCount.textContent = cap.value.length;
    capBox.classList.toggle('is-full', cap.value.length >= MAX_CAPTION);
  }
  cap.addEventListener('input', updateCap);

  /* ---------- Hashtag chip ---------- */
  const chipbox = $('chipbox'), tagInput = $('tag-input'), tagsValue = $('tags-value');
  let tags = [];

  function renderTags() {
    chipbox.querySelectorAll('.mp-chip').forEach(n => n.remove());
    tags.forEach((t, i) => {
      const chip = document.createElement('span');
      chip.className = 'mp-chip';
      chip.append('#' + t);
      const x = document.createElement('button');
      x.type = 'button';
      x.textContent = '×';
      x.setAttribute('aria-label', 'Hapus ' + t);
      x.addEventListener('click', () => { tags.splice(i, 1); renderTags(); tagInput.focus(); });
      chip.append(x);
      chipbox.insertBefore(chip, tagInput);
    });
    tagsValue.value = tags.join(',');
    tagInput.disabled = tags.length >= MAX_TAGS;
  }

  function addTag() {
    const v = tagInput.value.replace(/[^\p{L}\p{N}_]/gu, '').slice(0, 30).toLowerCase();
    tagInput.value = '';
    if (v && tags.length < MAX_TAGS && !tags.includes(v)) { tags.push(v); renderTags(); }
  }

  tagInput.addEventListener('keydown', e => {
    if (['Enter', ',', ' '].includes(e.key)) { e.preventDefault(); addTag(); }
    if (e.key === 'Backspace' && !tagInput.value && tags.length) { tags.pop(); renderTags(); }
  });
  tagInput.addEventListener('blur', addTag);
  chipbox.addEventListener('click', () => tagInput.focus());

  /* ---------- Buka modal (event delegation) ---------- */
  grid.addEventListener('click', e => {
    const editBtn = e.target.closest('[data-edit]');
    const delBtn = e.target.closest('[data-delete]');

    if (editBtn) {
      currentCard = editBtn.closest('.myposts-card');
      editForm.action = editBtn.dataset.action;
      $('edit-img').src = editBtn.dataset.img;
      cap.value = currentCard.querySelector('[data-caption]').textContent.trim().slice(0, MAX_CAPTION);
      tags = [...currentCard.querySelectorAll('.myposts-tag')].map(n => n.textContent.trim());
      $('edit-error').textContent = '';
      renderTags();
      updateCap();
      editModal.showModal();
      cap.focus();
    }

    if (delBtn) {
      currentCard = delBtn.closest('.myposts-card');
      delForm.action = delBtn.dataset.action;
      $('delete-img').src = delBtn.dataset.img;
      $('delete-error').textContent = '';
      delModal.showModal();
    }
  });

  /* ---------- Simpan edit tanpa reload ---------- */
  editForm.addEventListener('submit', async e => {
    e.preventDefault();
    addTag();   // hashtag yang masih diketik ikut tersimpan
    const btn = $('edit-submit');
    btn.disabled = true;
    btn.textContent = 'Menyimpan...';
    try {
      const data = await send(editForm);
      currentCard.querySelector('[data-caption]').textContent = data.caption;
      currentCard.querySelector('[data-tags]').replaceChildren(
        ...data.hashtags.map(h => {
          const s = document.createElement('span');
          s.className = 'myposts-tag';
          s.textContent = h;
          return s;
        })
      );
      editModal.close();
      toast('Perubahan berhasil disimpan.');
    } catch {
      $('edit-error').textContent = 'Gagal menyimpan. Coba lagi.';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Simpan perubahan';
    }
  });

  /* ---------- Hapus tanpa reload ---------- */
  delForm.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = $('delete-submit');
    btn.disabled = true;
    btn.textContent = 'Menghapus...';
    try {
      const data = await send(delForm);
      delModal.close();
      const card = currentCard;
      card.classList.add('is-removing');
      setTimeout(() => {
        card.remove();
        totalEl.textContent = data.total;
        if (!data.total) {
          grid.hidden = true;
          uploadTop.hidden = true;
          empty.hidden = false;
        }
      }, 300);
      toast('Postingan dihapus.');
    } catch {
      $('delete-error').textContent = 'Gagal menghapus. Coba lagi.';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Hapus';
    }
  });

  const flash = $('toast').dataset.flash;
  if (flash) toast(flash);

  /* ---------- Tutup modal ---------- */
  document.querySelectorAll('[data-close]').forEach(b =>
    b.addEventListener('click', () => b.closest('dialog').close()));
  [editModal, delModal].forEach(d =>
    d.addEventListener('click', e => { if (e.target === d) d.close(); }));
})();