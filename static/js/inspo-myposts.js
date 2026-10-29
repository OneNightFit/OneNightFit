(() => {
  const $ = id => document.getElementById(id);
  const grid = $('grid');
  if (!grid) return;

  const empty = $('empty'), totalEl = $('total'), uploadTop = $('upload-top');
  const delModal = $('delete-modal'), delForm = $('delete-form');
  let currentCard = null;

  let toastTimer;
  function toast(msg) {
    const t = $('toast');
    t.textContent = msg;
    t.classList.add('is-show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('is-show'), 2500);
  }

  async function send(form) {
    const res = await fetch(form.action, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: new FormData(form),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  grid.addEventListener('click', e => {
    const delBtn = e.target.closest('[data-delete]');
    if (!delBtn) return;
    currentCard = delBtn.closest('.myposts-card');
    delForm.action = delBtn.dataset.action;
    $('delete-img').src = delBtn.dataset.img;
    $('delete-error').textContent = '';
    delModal.showModal();
  });

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

  document.querySelectorAll('[data-close]').forEach(b =>
    b.addEventListener('click', () => b.closest('dialog').close()));
  delModal.addEventListener('click', e => { if (e.target === delModal) delModal.close(); });

  const flash = $('toast').dataset.flash;
  if (flash) toast(flash);
})();