document.addEventListener('DOMContentLoaded', () => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const status = document.querySelector('[data-live-edit-status]');
  const saveEndpoint = '/admin/live-edit/save';
  const styleEndpoint = '/admin/live-edit/style';
  let activeEl = null;

  function setStatus(text, state) {
    if (!status) return;
    status.textContent = text;
    status.dataset.state = state || '';
  }

  function editableLabel(el) {
    if (!el) return 'field';
    const target = el.dataset.liveTarget || '';
    const field = el.dataset.liveField || '';
    const id = el.dataset.liveId || '';
    return `${target}.${field}${id ? ':' + id : ''}`;
  }

  async function postJson(url, payload) {
    if (!csrf) throw new Error('CSRF token missing. Hard refresh the page, then login again.');
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-CSRF-Token': csrf
      },
      body: JSON.stringify(payload)
    });
    const contentType = res.headers.get('content-type') || '';
    let data = {};
    if (contentType.includes('application/json')) {
      data = await res.json();
    } else {
      const text = await res.text();
      data = {error: text.slice(0, 180) || 'Server returned a non-JSON error.'};
    }
    if (!res.ok || !data.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  async function saveElement(el) {
    if (!el) return;
    const next = (el.innerText || el.textContent || '').trim();
    const original = el.dataset.liveOriginal || '';
    if (next === original) return;
    setStatus('Saving ' + editableLabel(el) + '...', 'saving');
    el.classList.add('live-edit-saving');
    try {
      await postJson(saveEndpoint, {
        target: el.dataset.liveTarget,
        field: el.dataset.liveField,
        id: el.dataset.liveId || '',
        value: next
      });
      el.dataset.liveOriginal = next;
      el.classList.remove('live-edit-error');
      el.classList.add('live-edit-saved');
      setStatus('Saved. Public website updated.', 'saved');
      setTimeout(() => el.classList.remove('live-edit-saved'), 1200);
    } catch (err) {
      el.classList.add('live-edit-error');
      setStatus(err.message || 'Save failed.', 'error');
      console.error('Live edit save failed', err);
    } finally {
      el.classList.remove('live-edit-saving');
    }
  }

  function applyPreviewStyle(el, prop, value) {
    if (!el) return;
    if (prop === 'font') el.style.fontFamily = value ? `'${value}', system-ui, sans-serif` : '';
    if (prop === 'size') el.style.fontSize = value || '';
    if (prop === 'weight') el.style.fontWeight = value || '';
    if (prop === 'italic') el.style.fontStyle = value === '1' ? 'italic' : '';
    if (prop === 'uppercase') el.style.textTransform = value === '1' ? 'uppercase' : '';
    if (prop === 'color') el.style.color = value || '';
    if (prop === 'align') el.style.textAlign = value || '';
  }

  async function saveStyle(props) {
    if (!activeEl) {
      setStatus('Select editable text first.', 'error');
      return;
    }
    Object.entries(props).forEach(([prop, value]) => applyPreviewStyle(activeEl, prop, value));
    setStatus('Saving style for ' + editableLabel(activeEl) + '...', 'saving');
    try {
      await postJson(styleEndpoint, {
        target: activeEl.dataset.liveTarget,
        field: activeEl.dataset.liveField,
        id: activeEl.dataset.liveId || '',
        props
      });
      setStatus('Style saved.', 'saved');
    } catch (err) {
      setStatus(err.message || 'Style save failed.', 'error');
      console.error('Live edit style failed', err);
    }
  }

  function activate(el) {
    activeEl = el;
    document.querySelectorAll('.live-edit-field.live-edit-active').forEach(x => x.classList.remove('live-edit-active'));
    el.classList.add('live-edit-active');
    setStatus('Editing ' + editableLabel(el) + '. Click outside or press Ctrl+S to save.', 'editing');
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
      activate(el);
      el.focus();
    });
    el.addEventListener('focus', () => activate(el));
    el.addEventListener('blur', () => {
      el.classList.remove('live-edit-active');
      saveElement(el);
    });
    el.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveElement(el);
      }
      if (event.key === 'Escape') {
        event.preventDefault();
        el.innerText = el.dataset.liveOriginal || '';
        el.blur();
      }
    });
  });

  document.querySelector('[data-live-save]')?.addEventListener('click', () => saveElement(activeEl));
  document.querySelector('[data-style-font]')?.addEventListener('change', e => saveStyle({font: e.target.value}));
  document.querySelector('[data-style-size]')?.addEventListener('change', e => saveStyle({size: e.target.value.trim()}));
  document.querySelector('[data-style-color]')?.addEventListener('input', e => saveStyle({color: e.target.value}));
  document.querySelector('[data-style-align]')?.addEventListener('change', e => saveStyle({align: e.target.value}));
  document.querySelector('[data-style-bold]')?.addEventListener('click', () => {
    const current = activeEl && (activeEl.style.fontWeight || getComputedStyle(activeEl).fontWeight);
    saveStyle({weight: current && parseInt(current, 10) >= 700 ? '' : '800'});
  });
  document.querySelector('[data-style-italic]')?.addEventListener('click', () => {
    const current = activeEl && getComputedStyle(activeEl).fontStyle === 'italic';
    saveStyle({italic: current ? '0' : '1'});
  });

  const backdrop = document.querySelector('[data-live-modal-backdrop]');
  function openModal(name) {
    if (!backdrop) return;
    backdrop.hidden = false;
    backdrop.querySelectorAll('[data-live-modal-panel]').forEach(p => p.hidden = p.dataset.liveModalPanel !== name);
  }
  function closeModal() {
    if (backdrop) backdrop.hidden = true;
  }
  document.querySelectorAll('[data-modal-open]').forEach(btn => btn.addEventListener('click', () => openModal(btn.dataset.modalOpen)));
  document.querySelectorAll('[data-modal-close]').forEach(btn => btn.addEventListener('click', closeModal));
  backdrop?.addEventListener('click', e => { if (e.target === backdrop) closeModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  setStatus('Live Editor ready. Click highlighted text to edit.', 'ready');
});
