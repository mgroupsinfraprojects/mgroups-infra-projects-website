document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('[data-nav-toggle]');
  const nav = document.querySelector('[data-nav]');
  if (toggle && nav) {
    toggle.addEventListener('click', () => nav.classList.toggle('open'));
    document.addEventListener('click', (e) => {
      if (!nav.contains(e.target) && !toggle.contains(e.target)) nav.classList.remove('open');
    });
  }
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
      if (!confirm(form.dataset.confirm || 'Are you sure?')) e.preventDefault();
    });
  });
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => { el.style.opacity = '0'; }, 4500);
    setTimeout(() => { el.remove(); }, 5200);
  });

  function enableReorder(container) {
    let dragging = null;
    const kind = container.dataset.reorderKind;
    const selector = container.tagName === 'TABLE' ? 'tr[data-id]' : '[data-id]';
    container.querySelectorAll(selector).forEach(item => {
      item.setAttribute('draggable', 'true');
      item.addEventListener('dragstart', () => { dragging = item; item.classList.add('dragging'); });
      item.addEventListener('dragend', () => { item.classList.remove('dragging'); dragging = null; saveOrder(container, selector, kind); });
      item.addEventListener('dragover', e => { e.preventDefault(); if (item !== dragging) item.classList.add('drop-target'); });
      item.addEventListener('dragleave', () => item.classList.remove('drop-target'));
      item.addEventListener('drop', e => {
        e.preventDefault(); item.classList.remove('drop-target');
        if (!dragging || dragging === item) return;
        const rect = item.getBoundingClientRect();
        const before = (e.clientY - rect.top) < rect.height / 2;
        if (before) item.parentNode.insertBefore(dragging, item); else item.parentNode.insertBefore(dragging, item.nextSibling);
      });
    });
  }
  function saveOrder(container, selector, kind) {
    const order = Array.from(container.querySelectorAll(selector)).map(el => el.dataset.id).filter(Boolean);
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
    if (!kind || !order.length) return;
    fetch(`/admin/reorder/${kind}`, {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':csrf}, body:JSON.stringify({order})})
      .then(r => { if (!r.ok) throw new Error('Reorder failed'); return r.json(); })
      .catch(() => alert('Order save failed. Refresh and try again.'));
  }
  document.querySelectorAll('[data-reorder-kind]').forEach(enableReorder);
});
