document.addEventListener('DOMContentLoaded', () => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const status = document.querySelector('[data-live-edit-status]');
  const endpoint = '/admin/live-edit/save';

  function setStatus(text, state) {
    if (!status) return;
    status.textContent = text;
    status.dataset.state = state || '';
  }

  function editableLabel(el) {
    const target = el.dataset.liveTarget || '';
    const field = el.dataset.liveField || '';
    const id = el.dataset.liveId || '';
    return `${target}.${field}${id ? ':' + id : ''}`;
  }

  async function saveElement(el) {
    const next = (el.innerText || el.textContent || '').trim();
    const original = el.dataset.liveOriginal || '';
    if (next === original) return;
    setStatus('Saving ' + editableLabel(el) + '...', 'saving');
    el.classList.add('live-edit-saving');
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
        body: JSON.stringify({
          target: el.dataset.liveTarget,
          field: el.dataset.liveField,
          id: el.dataset.liveId || '',
          value: next
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) throw new Error(data.error || 'Save failed');
      el.dataset.liveOriginal = next;
      el.classList.remove('live-edit-error');
      el.classList.add('live-edit-saved');
      setStatus('Saved. Public website updated.', 'saved');
      setTimeout(() => el.classList.remove('live-edit-saved'), 1200);
    } catch (err) {
      el.classList.add('live-edit-error');
      setStatus(err.message || 'Save failed. Refresh and try again.', 'error');
      alert(err.message || 'Save failed. Refresh and try again.');
    } finally {
      el.classList.remove('live-edit-saving');
    }
  }

  document.querySelectorAll('[data-live-edit="1"]').forEach(el => {
    el.setAttribute('contenteditable', 'true');
    el.setAttribute('spellcheck', 'true');
    el.setAttribute('tabindex', '0');
    el.classList.add('live-edit-field');
    el.dataset.liveOriginal = (el.innerText || el.textContent || '').trim();

    el.addEventListener('click', event => {
      if (el.tagName === 'A' || el.closest('a')) event.preventDefault();
      event.stopPropagation();
    });
    el.addEventListener('focus', () => {
      el.dataset.liveOriginal = (el.innerText || el.textContent || '').trim();
      el.classList.add('live-edit-active');
      setStatus('Editing ' + editableLabel(el) + '. Click outside to save.', 'editing');
    });
    el.addEventListener('blur', () => {
      el.classList.remove('live-edit-active');
      saveElement(el);
    });
    el.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        el.blur();
      }
      if (event.key === 'Escape') {
        event.preventDefault();
        el.innerText = el.dataset.liveOriginal || '';
        el.blur();
      }
    });
  });
});
