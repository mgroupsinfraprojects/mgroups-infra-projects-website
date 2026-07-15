function optionHtml(){ return materials.map(m=>`<option value="${m.id}" data-rate="${m.rate}">${m.name} (${m.unit})</option>`).join(''); }
function addItemRow(){
  const tr=document.createElement('tr');
  tr.innerHTML=`<td><select name="material_id[]" class="form-select material-select" onchange="setRate(this)">${optionHtml()}</select><div class="small-muted available-text"></div></td>
  <td><input name="quantity[]" type="number" step="0.01" min="0" class="form-control qty-input" placeholder="Qty"></td>
  <td class="rate-cell"><input name="rate[]" type="number" step="0.01" class="form-control rate-input" placeholder="Rate"></td>
  <td class="physical-cell"><input name="physical_quantity[]" type="number" step="0.01" min="0" class="form-control" placeholder="Physical"></td>
  <td class="usage-cell"><select name="usage_type[]" class="form-select usage-select" onchange="toggleCustomUsage(this)"><option value="">--</option><option>Used</option><option>Damaged</option><option>Wasted</option><option>Scrap</option><option>Missing</option><option>Other</option></select><input name="custom_usage_type[]" class="form-control mt-1 d-none custom-usage" placeholder="Type usage"></td>
  <td class="usage-cell"><input name="work_activity[]" class="form-control" placeholder="Work activity"></td>
  <td><input name="item_remarks[]" class="form-control" placeholder="Remarks"></td>
  <td><button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('tr').remove()">×</button></td>`;
  document.getElementById('itemsBody').appendChild(tr); setRate(tr.querySelector('.material-select')); refreshFields(); updateAvailableStock(tr);
}
function setRate(sel){ const rate=sel.options[sel.selectedIndex]?.dataset.rate||0; const row=sel.closest('tr'); const input=row.querySelector('.rate-input'); if(input && !input.value) input.value=rate; updateAvailableStock(row); }
function toggleCustomUsage(sel){ sel.closest('td').querySelector('.custom-usage').classList.toggle('d-none', sel.value!=='Other'); }
function selectMovementType(code){
  document.getElementById('movementType').value=code;
  document.querySelectorAll('.quick-card').forEach(c=>c.classList.toggle('selected', c.dataset.type===code));
  refreshFields();
  window.scrollTo({top:document.getElementById('movementForm').offsetTop-80, behavior:'smooth'});
}
async function updateAvailableStock(row){
  const from=document.getElementById('fromLocation')?.value;
  const mat=row.querySelector('.material-select')?.value;
  const target=row.querySelector('.available-text');
  const t=document.getElementById('movementType').value;
  const effect=document.getElementById('stockEffect').value;
  const needsAvailability=['STORE_TO_SITE','SITE_TO_SITE','SITE_TO_STORE_RETURN','SITE_CONSUMPTION','DAMAGE_MISSING','STOCK_ADJUSTMENT'].includes(t) || (t==='MISC' && ['DECREASE','TRANSFER'].includes(effect));
  if(!target || !from || !mat || !needsAvailability){ if(target) target.textContent=''; return; }
  try{
    const res=await fetch(`/api/stock/${from}/${mat}`);
    const data=await res.json();
    target.textContent=`Available at source: ${data.quantity}`;
  }catch(e){ target.textContent=''; }
}
function refreshFields(){
  const t=document.getElementById('movementType').value;
  const effect=document.getElementById('stockEffect').value;
  const isMisc=t==='MISC';
  const showSupplier = t==='PURCHASE_TO_STORE';
  let showFrom = ['STORE_TO_SITE','SITE_TO_SITE','SITE_TO_STORE_RETURN','SITE_CONSUMPTION','DAMAGE_MISSING','STOCK_ADJUSTMENT'].includes(t);
  let showTo = ['PURCHASE_TO_STORE','OPENING_STOCK','STORE_TO_SITE','SITE_TO_SITE','SITE_TO_STORE_RETURN'].includes(t);
  if(isMisc){ showFrom=['DECREASE','TRANSFER'].includes(effect); showTo=['INCREASE','TRANSFER'].includes(effect); }
  const showInvoice = t==='PURCHASE_TO_STORE';
  const showVehicle = ['STORE_TO_SITE','SITE_TO_SITE','SITE_TO_STORE_RETURN'].includes(t) || (isMisc && effect==='TRANSFER');
  const showUsage = ['SITE_CONSUMPTION','DAMAGE_MISSING'].includes(t);
  const showPhysical = t==='STOCK_ADJUSTMENT';
  const showRate = ['PURCHASE_TO_STORE','OPENING_STOCK'].includes(t) || (isMisc && effect==='INCREASE');
  document.querySelectorAll('.supplier-field').forEach(e=>e.classList.toggle('d-none', !showSupplier));
  document.querySelectorAll('.from-field').forEach(e=>e.classList.toggle('d-none', !showFrom));
  document.querySelectorAll('.to-field').forEach(e=>e.classList.toggle('d-none', !showTo));
  document.querySelectorAll('.invoice-field').forEach(e=>e.classList.toggle('d-none', !showInvoice));
  document.querySelectorAll('.vehicle-field,.proof-field,.dc-field').forEach(e=>e.classList.toggle('d-none', !showVehicle));
  document.querySelectorAll('.damage-field').forEach(e=>e.classList.toggle('d-none', t!=='DAMAGE_MISSING'));
  document.querySelectorAll('.custom-movement-field,.stock-effect-field').forEach(e=>e.classList.toggle('d-none', !isMisc));
  document.querySelectorAll('.usage-col,.usage-cell').forEach(e=>e.classList.toggle('d-none', !showUsage));
  document.querySelectorAll('.physical-col,.physical-cell').forEach(e=>e.classList.toggle('d-none', !showPhysical));
  document.querySelectorAll('.rate-col,.rate-cell').forEach(e=>e.classList.toggle('d-none', !showRate));
  document.querySelectorAll('input[name="quantity[]"]').forEach(e=>e.placeholder = showPhysical ? 'Not needed' : 'Qty');
  document.querySelectorAll('#itemsBody tr').forEach(updateAvailableStock);
  document.querySelectorAll('.quick-card').forEach(c=>c.classList.toggle('selected', c.dataset.type===t));
}
document.getElementById('movementType').addEventListener('change', refreshFields);
document.getElementById('stockEffect').addEventListener('change', refreshFields);
document.getElementById('fromLocation').addEventListener('change', refreshFields);
if (typeof selectedType !== 'undefined' && selectedType) document.getElementById('movementType').value=selectedType;
addItemRow(); refreshFields();
