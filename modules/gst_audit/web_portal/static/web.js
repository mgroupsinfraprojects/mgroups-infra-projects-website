const payloadNode = document.getElementById('payload');
function parsePayload(){
  const raw = payloadNode?.textContent || '{}';
  try { return JSON.parse(raw); }
  catch (err) {
    const errorBox = document.getElementById('error');
    if(errorBox) errorBox.textContent = 'Dashboard data could not be loaded. Restart web mode and try again.';
    console.error('GST Audit dashboard JSON parse failed', err);
    return {has_result:false, summary:{}, months:[], sources:[], suppliers:[], review_rows:[], approved_preview:[], invoice_rows:[]};
  }
}
const data = parsePayload();
function $(id){ return document.getElementById(id); }
function safe(value){return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function money(value){ return '₹' + safe(value || '0.00'); }
function metric(label, value, extra='', cls=''){
  return `<div class="metric ${safe(cls)}"><span>${safe(label)}</span><strong>${safe(value)}</strong>${extra ? `<p class="muted">${safe(extra)}</p>`:''}</div>`;
}
function installChrome(){
  if($('version')) $('version').textContent = `${data.app_name || 'GST Audit Pro'} v${data.version || ''}`;
}
function table(rows, columns, limit=500, opts={}){
  if(!rows || rows.length === 0) return '<p class="muted">No data to show.</p>';
  const shown = rows.slice(0, limit);
  const head = '<tr>' + columns.map(c => `<th>${safe(c.label)}</th>`).join('') + '</tr>';
  const body = shown.map(row => {
    const attrs = opts.rowAttrs ? opts.rowAttrs(row) : '';
    return `<tr ${attrs}>` + columns.map(c => `<td>${safe(typeof c.value === 'function' ? c.value(row) : row[c.key])}</td>`).join('') + '</tr>';
  }).join('');
  const suffix = rows.length > shown.length ? `<p class="muted table-note">Showing ${shown.length} of ${rows.length} rows. Use search/export for full data.</p>` : '';
  return `<table><thead>${head}</thead><tbody>${body}</tbody></table>${suffix}`;
}
function metricsHtml(){
  if(!data.has_result) return metric('Status','Waiting for files','Upload Excel/CSV files to start audit.');
  const s = data.summary || {};
  return [
    metric('Invoice Value', money(s.invoice_value), `${s.approved_rows || 0} approved invoice rows`),
    metric('Taxable Value', money(s.taxable_value), 'approved invoice rows only'),
    metric('Total GST', money(s.total_gst), 'IGST + CGST + SGST + Cess'),
    metric('Review Rows', s.review_rows || 0, 'real invoice issues only', Number(s.review_rows) ? 'status-warn' : 'status-ok'),
    metric('Invoice Data Rows', s.web_invoice_rows || 0, 'rows with company + GSTIN + invoice no + value'),
    metric('Suppliers', s.suppliers || 0, 'unique GSTIN/supplier'),
    metric('Raw Rows Read', s.raw_rows_read || 0, `${s.trace_rows || 0} support/header rows excluded from web action`),
    metric('Status', s.final_status || 'NO_DATA', s.row_coverage_status && s.amount_reconciliation_status ? `${s.row_coverage_status} / ${s.amount_reconciliation_status}` : ''),
  ].join('');
}
function decisionForm(row, action, label, cls=''){
  return `<form action="/review" method="post" class="mini-form">
    <input type="hidden" name="row_id" value="${safe(row.row_id)}">
    <input type="hidden" name="action" value="${safe(action)}">
    <input type="hidden" name="note" value="Decision saved from web mode.">
    <button class="${safe(cls)}" type="submit">${safe(label)}</button>
  </form>`;
}
function reviewTable(rows){
  if(!rows || rows.length === 0) return '<p class="muted">No real invoice review rows pending. Header/support rows are excluded.</p>';
  const cols = [
    {key:'supplier_name',label:'Company'},
    {key:'gstin',label:'GSTIN'},
    {key:'invoice_no',label:'Invoice No'},
    {key:'invoice_date',label:'Date'},
    {key:'taxable_value',label:'Taxable'},
    {key:'gst',label:'GST'},
    {key:'invoice_value',label:'Invoice Value'},
    {key:'difference',label:'Diff'},
    {key:'reason',label:'Issue'},
    {label:'Action', value:(row)=>''},
  ];
  const head = '<tr>' + cols.map(c => `<th>${safe(c.label)}</th>`).join('') + '</tr>';
  const body = rows.map(row => `<tr>
    <td>${safe(row.supplier_name)}</td><td>${safe(row.gstin)}</td><td>${safe(row.invoice_no)}</td><td>${safe(row.invoice_date)}</td>
    <td>${safe(row.taxable_value)}</td><td>${safe(row.gst)}</td><td>${safe(row.invoice_value)}</td><td>${safe(row.difference)}</td><td>${safe(row.reason)}</td>
    <td><div class="row-actions">${decisionForm(row,'approve','Approve')}${decisionForm(row,'reject','Reject','reject')}${decisionForm(row,'ignore','Ignore','ignore')}</div></td>
  </tr>`).join('');
  return `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
}
function supplierTable(rows){
  return table(rows || [], [
    {key:'supplier_name', label:'Supplier'},
    {key:'gstin', label:'GSTIN'},
    {key:'invoices', label:'Invoices'},
    {key:'approved_rows', label:'Approved'},
    {key:'review_rows', label:'Review'},
    {key:'invoice_value', label:'Invoice Value'},
    {key:'taxable_value', label:'Taxable'},
    {key:'gst', label:'GST'},
  ], 500, {rowAttrs:(row)=>`data-supplier-key="${safe(row.key)}" class="clickable-row"`});
}
function invoiceDataTable(rows, limit=250){
  return table(rows || [], [
    {key:'source_file',label:'Source'},
    {key:'supplier_name',label:'Company'},
    {key:'gstin',label:'GSTIN'},
    {key:'invoice_no',label:'Invoice No'},
    {key:'invoice_date',label:'Date'},
    {key:'taxable_value',label:'Taxable'},
    {key:'gst',label:'GST'},
    {key:'invoice_value',label:'Invoice Value'},
    {key:'status',label:'Status'},
  ], limit);
}
function monthTable(rows){
  return table(rows || [], [
    {key:'month', label:'Month'},
    {key:'rows', label:'Invoice Rows'},
    {key:'approved_rows', label:'Approved'},
    {key:'review_rows', label:'Review'},
    {key:'suppliers', label:'Suppliers'},
    {key:'invoice_value', label:'Invoice Value'},
    {key:'taxable_value', label:'Taxable'},
    {key:'gst', label:'GST'},
  ], 100);
}
function sourceTable(rows){
  return table(rows || [], [
    {key:'source', label:'File'},
    {key:'rows', label:'Invoice Rows'},
    {key:'approved_rows', label:'Approved'},
    {key:'review_rows', label:'Review'},
    {key:'suppliers', label:'Suppliers'},
    {key:'invoice_value', label:'Invoice Value'},
  ], 100);
}
function barChart(rows, key){
  if(!rows || rows.length === 0) return '<p class="muted">No chart data.</p>';
  const max = Math.max(...rows.map(r => Number(r.value_raw || 0)), 1);
  return rows.map(r => {
    const pct = Math.max(1, Math.round((Number(r.value_raw || 0) / max) * 100));
    const label = r[key] || r.label || 'Unknown';
    return `<div class="bar-row"><span>${safe(label)}</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div><b>₹${safe(r.invoice_value)}</b></div>`;
  }).join('');
}
function filterTable(inputId, containerId){
  const input = $(inputId), container = $(containerId);
  if(!input || !container) return;
  input.addEventListener('input', () => {
    const query = input.value.trim().toLowerCase();
    container.querySelectorAll('tbody tr').forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(query) ? '' : 'none';
    });
  });
}
function installSupplierClicks(){
  const tableBox = $('suppliersTable');
  if(!tableBox) return;
  tableBox.querySelectorAll('tr[data-supplier-key]').forEach(row => {
    row.addEventListener('click', () => {
      tableBox.querySelectorAll('tr').forEach(r => r.classList.remove('selected-row'));
      row.classList.add('selected-row');
      const key = row.getAttribute('data-supplier-key');
      const supplier = (data.suppliers || []).find(s => s.key === key);
      const invoices = (data.invoice_rows || []).filter(inv => String((inv.gstin || inv.supplier_name || '').toUpperCase()) === key);
      if($('selectedSupplierTitle')) $('selectedSupplierTitle').textContent = `${supplier?.supplier_name || 'Selected Supplier'} — Invoice Details`;
      if($('selectedSupplierMeta')) $('selectedSupplierMeta').textContent = `${supplier?.gstin || ''} · ${invoices.length} invoice row(s)`;
      if($('supplierInvoices')) $('supplierInvoices').innerHTML = invoiceDataTable(invoices, 500);
    });
  });
}
function renderApp(){
  installChrome();
  if($('dashboard')) $('dashboard').innerHTML = metricsHtml();
  if($('monthChart')) $('monthChart').innerHTML = barChart(data.months || [], 'month');
  if($('sourceChart')) $('sourceChart').innerHTML = barChart(data.sources || [], 'source');
  if($('monthTable')) $('monthTable').innerHTML = data.has_result ? monthTable(data.months || []) : '<p class="muted">No audit loaded.</p>';
  if($('sourceTable')) $('sourceTable').innerHTML = data.has_result ? sourceTable(data.sources || []) : '<p class="muted">No audit loaded.</p>';
  if($('reviewRows')) $('reviewRows').innerHTML = data.has_result ? reviewTable(data.review_rows || []) : '<p class="muted">No audit loaded.</p>';
  if($('suppliersTable')) $('suppliersTable').innerHTML = data.has_result ? supplierTable(data.suppliers || []) : '<p class="muted">No audit loaded.</p>';
  if($('approvedRows')) $('approvedRows').innerHTML = data.has_result ? invoiceDataTable(data.approved_preview || [], 250) : '<p class="muted">No audit loaded.</p>';
  if($('supplierInvoices')) $('supplierInvoices').innerHTML = '<p class="muted">Click a supplier row to view invoices.</p>';
  filterTable('reviewSearch', 'reviewRows');
  filterTable('supplierSearch', 'suppliersTable');
  filterTable('invoiceSearch', 'approvedRows');
  installSupplierClicks();
}
function installUploadFeedback(){
  document.querySelectorAll('form.upload-form').forEach(form => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('button[type=submit]');
      const status = document.getElementById('uploadStatus');
      if(button){ button.disabled = true; button.textContent = 'Auditing...'; }
      if(status){ status.textContent = 'Processing file. Do not close this tab.'; status.classList.remove('hidden'); }
    });
  });
}
function renderReport(){
  if(!$('reportMetrics')) return;
  $('reportMeta').textContent = `${data.app_name || 'GST Audit Pro'} v${data.version || ''} · Files: ${(data.files || []).join(', ') || 'No file loaded'}`;
  $('reportMetrics').innerHTML = metricsHtml();
  if($('reportMonths')) $('reportMonths').innerHTML = monthTable(data.months || []);
  if($('reportSuppliers')) $('reportSuppliers').innerHTML = supplierTable(data.suppliers || []);
  if($('reportReview')) $('reportReview').innerHTML = reviewTable(data.review_rows || []);
}
renderApp();
renderReport();
installUploadFeedback();
