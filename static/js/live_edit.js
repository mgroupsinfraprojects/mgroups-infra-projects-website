document.addEventListener('DOMContentLoaded', () => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const status = document.querySelector('[data-live-edit-status]');
  const saveEndpoint = '/admin/live-edit/save';
  const styleEndpoint = '/admin/live-edit/style';
  let activeEl = null;
  let activeOriginal = '';

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
    if (!csrf) throw new Error('CSRF token missing. Hard refresh, login again, then retry.');
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
      data = { error: text.slice(0, 220) || `Server returned HTTP ${res.status}` };
    }

    if (!res.ok || !data.ok) {
      if (res.status === 401 || res.status === 403) throw new Error('Login/session/CSRF blocked the save. Login again and hard refresh.');
      if (res.status === 429) throw new Error('Too many save attempts. Wait a few minutes and retry.');
      throw new Error(data.error || `Request failed (${res.status})`);
    }
    return data;
  }

  function buildEditorPanel() {
    const panel = document.createElement('section');
    panel.className = 'live-editor-sidepanel';
    panel.hidden = true;
    panel.innerHTML = `
      <div class="live-editor-sidepanel-head">
        <div>
          <small>Selected field</small>
          <strong data-panel-field>None</strong>
        </div>
        <button type="button" data-panel-close aria-label="Close editor">×</button>
      </div>
      <label class="live-editor-panel-label">Content</label>
      <textarea data-panel-value rows="7" spellcheck="true"></textarea>
      <div class="live-editor-panel-actions">
        <button type="button" data-panel-save>Save Text</button>
        <button type="button" data-panel-cancel>Cancel</button>
      </div>
      <p class="live-editor-panel-help">Click text on the page, edit here, then save. This avoids browser inline-edit glitches.</p>
    `;
    document.body.appendChild(panel);
    return panel;
  }

  const panel = buildEditorPanel();
  const panelField = panel.querySelector('[data-panel-field]');
  const panelValue = panel.querySelector('[data-panel-value]');

  function openPanelFor(el) {
    activeEl = el;
    activeOriginal = (el.innerText || el.textContent || '').trim();
    panelField.textContent = editableLabel(el);
    panelValue.value = activeOriginal;
    panel.hidden = false;
    setTimeout(() => panelValue.focus(), 0);
  }

  function closePanel() {
    panel.hidden = true;
  }

  function activate(el) {
    document.querySelectorAll('.live-edit-field.live-edit-active').forEach(x => x.classList.remove('live-edit-active'));
    activeEl = el;
    el.classList.add('live-edit-active');
    setStatus('Selected ' + editableLabel(el) + '. Edit in the side panel.', 'editing');
    openPanelFor(el);
  }

  async function saveValue(el, value) {
    if (!el) {
      setStatus('Select editable text first.', 'error');
      return;
    }
    const next = (value ?? '').trim();
    const original = (el.dataset.liveOriginal || activeOriginal || '').trim();
    if (next === original) {
      setStatus('No change to save.', 'ready');
      return;
    }

    setStatus('Saving ' + editableLabel(el) + '...', 'saving');
    el.classList.add('live-edit-saving');
    try {
      await postJson(saveEndpoint, {
        target: el.dataset.liveTarget,
        field: el.dataset.liveField,
        id: el.dataset.liveId || '',
        value: next
      });
      el.textContent = next;
      el.dataset.liveOriginal = next;
      activeOriginal = next;
      panelValue.value = next;
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

  async function savePanel() {
    await saveValue(activeEl, panelValue.value);
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

  document.querySelectorAll('[data-live-edit="1"]').forEach(el => {
    // Stable mode: no contenteditable. Editing happens in a controlled side panel.
    el.removeAttribute('contenteditable');
    el.setAttribute('tabindex', '0');
    el.classList.add('live-edit-field');
    el.dataset.liveOriginal = (el.innerText || el.textContent || '').trim();

    el.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      activate(el);
    });
    el.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        activate(el);
      }
    });
  });

  panel.querySelector('[data-panel-close]')?.addEventListener('click', closePanel);
  panel.querySelector('[data-panel-save]')?.addEventListener('click', savePanel);
  panel.querySelector('[data-panel-cancel]')?.addEventListener('click', () => {
    if (activeEl) panelValue.value = activeOriginal || activeEl.dataset.liveOriginal || '';
    closePanel();
    setStatus('Edit cancelled.', 'ready');
  });

  document.querySelector('[data-live-save]')?.addEventListener('click', savePanel);
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

  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      savePanel();
    }
    if (e.key === 'Escape' && !panel.hidden) closePanel();
  });

  const backdrop = document.querySelector('[data-live-modal-backdrop]');
  function openModal(name) {
    if (!backdrop) return;
    closePanel();
    backdrop.hidden = false;
    backdrop.querySelectorAll('[data-live-modal-panel]').forEach(p => p.hidden = p.dataset.liveModalPanel !== name);
  }
  function closeModal() {
    if (backdrop) backdrop.hidden = true;
  }
  document.querySelectorAll('[data-modal-open]').forEach(btn => btn.addEventListener('click', () => openModal(btn.dataset.modalOpen)));
  document.querySelectorAll('[data-modal-close]').forEach(btn => btn.addEventListener('click', closeModal));
  backdrop?.addEventListener('click', e => { if (e.target === backdrop) closeModal(); });

  setStatus('Live Editor ready. Click highlighted text to edit in the side panel.', 'ready');
});
