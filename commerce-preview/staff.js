'use strict';

const API = '/api/commerce';
const $ = (selector) => document.querySelector(selector);
const esc = (value = '') => String(value ?? '').replace(/[&<>"']/g,(c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (value) => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR'}).format(Number(value || 0) / 100);
const date = (value) => { const parsed = new Date(value); return Number.isNaN(parsed.valueOf()) ? '—' : new Intl.DateTimeFormat('en-IN',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Kolkata'}).format(parsed); };
const label = (value) => String(value || 'unknown').replaceAll('_',' ').replace(/^./, c => c.toUpperCase());
const kind = (value) => /refund/.test(value) ? 'refunded' : /^(paid|confirmed)$/.test(value) ? 'paid' : /fail|cancel|expire/.test(value) ? 'failed' : 'pending';
const descriptions = {owner:'Owner preview can inspect all test orders and the notification outbox.',sales:'Assigned salesperson preview sees only orders assigned to the test salesperson. Notification access is restricted.',unassigned_sales:'This salesperson has no assigned test orders. Other salespeople’s orders remain hidden.',purchase:'Purchase has no commerce order or notification permission in this staging preview.'};
const state = {token:null,role:'owner',orders:[],outbox:[],selected:null,busy:false,version:0,refundEvents:{}};
async function api(path, options = {}) {
  let response;
  try { response = await fetch(API + path,{credentials:'same-origin',cache:'no-store',...options,headers:{'Content-Type':'application/json',...(state.token ? {Authorization:`Bearer ${state.token}`} : {}),...options.headers},signal:AbortSignal.timeout(15000)}); }
  catch { throw new Error('The local preview could not be reached. Keep the preview server running and try again.'); }
  let data; try { data = await response.json(); } catch { throw new Error('The preview returned an unreadable response.'); }
  if (!response.ok) { const error = new Error(data.error?.message || 'This view is unavailable.'); error.code = data.error?.code; error.status = response.status; throw error; }
  return data;
}
function badge(status) { return `<span class="status-badge ${kind(status)}">${esc(label(status))}</span>`; }
function renderSummary() {
  const values = [ [state.orders.length,'Visible test orders'],[state.orders.filter(order => kind(order.status) === 'pending').length,'Awaiting payment'],[state.orders.filter(order => kind(order.status) === 'paid').length,'Paid test orders'],[state.outbox.length,'Notification previews'] ];
  $('#staff-summary').innerHTML = values.map(([value,title]) => `<div class="summary-stat"><strong>${value}</strong><span>${title}</span></div>`).join('');
}
function renderOrders() {
  const status = $('#status-filter').value;
  const orders = state.orders.filter(order => status === 'all' || kind(order.status) === status);
  if (!orders.length) { $('#orders-list').innerHTML = `<div class="empty-state">${state.role === 'purchase' ? 'This role does not have access to commerce orders.' : state.role === 'unassigned_sales' ? 'No orders are assigned to this salesperson.' : state.orders.length ? 'No test orders match this status.' : 'No test orders yet. Complete a test checkout to review its order record here.'}</div>`; return; }
  $('#orders-list').innerHTML = orders.map(order => `<article class="order-row"><div><strong>${esc(order.id)}</strong><small>${esc(date(order.created_at))} IST</small></div><div class="order-customer"><strong>${esc(order.buyer?.name || 'Test customer')}</strong><small>${esc(order.address?.city || '')} · ${esc(order.address?.postcode || '')}</small></div><div class="order-money"><strong>${money(order.total_paise)}</strong><small>${(order.items || order.quote?.items || []).reduce((sum,item) => sum + Number(item.quantity || 0),0)} test sheets</small></div>${badge(order.status)}<button type="button" class="text-button order-open" data-order="${esc(order.id)}" aria-label="View test order ${esc(order.id)}">Details →</button></article>`).join('');
}
function renderOutbox(error) {
  if (error) { $('#outbox-list').innerHTML = `<div class="empty-state">${error.status === 403 ? 'Notification outbox access is restricted to authorised owners.' : esc(error.message)}</div>`; return; }
  if (!state.outbox.length) { $('#outbox-list').innerHTML = '<div class="empty-state">No notifications queued yet. Test order and payment events will appear here without sending email.</div>'; return; }
  $('#outbox-list').innerHTML = state.outbox.map(item => `<article class="outbox-row"><div><strong>${esc(label(item.event))}</strong><small>${esc(item.order_id)}</small><small>${esc(date(item.created_at))} IST</small></div><div class="outbox-recipient"><strong>${esc(item.recipient)}</strong><small>${esc(item.payload?.subject || 'Test order notification')}</small></div><span class="status-badge">Preview only</span></article>`).join('');
}
function renderDetail(id, focus = true) {
  const order = state.orders.find(order => order.id === id);
  if (!order) { $('#order-detail').hidden = true; return; }
  state.selected = id;
  const quote = order.quote || order; const items = order.items || quote.items || []; const buyer = order.buyer || {}; const address = order.address || {};
  $('#order-detail-content').innerHTML = `<div class="receipt-lines"><div><span>Order reference</span><strong>${esc(order.id)}</strong></div><div><span>Current state</span>${badge(order.status)}</div><div><span>Recorded</span>${esc(date(order.created_at))} IST</div><div><span>Assigned salesperson</span>${esc(order.assigned_email || 'Unassigned')}</div></div><div class="review-address"><div><h3>Test customer</h3><p>${esc(buyer.name)}</p><p>${esc(buyer.email)}</p><p>${esc(buyer.phone)}</p>${buyer.company ? `<p>${esc(buyer.company)}</p>` : ''}</div><div><h3>Test delivery</h3><p>${esc(address.line1)}</p>${address.line2 ? `<p>${esc(address.line2)}</p>` : ''}<p>${esc(address.city)}, ${esc(address.state)} ${esc(address.postcode)}</p></div></div><ul class="review-items">${items.map(item => `<li><span><strong>${esc(item.name || item.sku)}</strong><span class="muted">${esc(item.sku)} · ${item.quantity} ${item.quantity === 1 ? 'sheet' : 'sheets'} × ${money(item.unit_price_paise)}</span></span><strong>${money(item.line_total_paise)}</strong></li>`).join('')}</ul><div class="totals"><div class="total-row"><span>Sheets</span><span>${money(quote.subtotal_paise)}</span></div><div class="total-row"><span>Delivery</span><span>${money(quote.shipping_paise)}</span></div><div class="total-row"><span>Included synthetic tax</span><span>${money(quote.tax_paise)}</span></div><div class="total-row grand-total"><span>Test total</span><span>${money(order.total_paise)}</span></div></div>${kind(order.status) === 'pending' ? `<p class="read-only-note">Reservation expires ${esc(date(order.expires_at))} IST. No fulfilment is authorised while payment is pending.</p>` : ''}${kind(order.status) === 'refunded' ? '<p class="test-callout"><strong>Stock review required.</strong> A refund does not prove that goods were returned. Paid sheets are not automatically put back into available stock.</p>' : ''}<p class="read-only-note">Immutable item, price and address snapshots are stored by the local backend. This is a staging review, separate from production staff records.</p>${state.role === 'owner' && kind(order.status) === 'paid' ? '<div class="detail-actions"><button class="button secondary" type="button" id="staff-refund">Simulate full refund</button></div>' : ''}<div id="detail-error" class="form-errors" role="alert" hidden></div>`;
  if (buyer.gstin) { const line = document.createElement('p'); line.textContent = 'GSTIN: ' + buyer.gstin; $('#order-detail-content .review-address>div').append(line); }
  if (quote.delivery_window) { const line = document.createElement('p'); line.className = 'read-only-note'; line.textContent = `Stored test delivery window: ${quote.delivery_window.min_days}–${quote.delivery_window.max_days} days. Policy version: ${quote.policy_version || '—'}.`; $('#order-detail-content').append(line); }
  $('#order-detail').hidden = false;
  if (focus) { $('#order-detail-title').focus({preventScroll:true}); $('#order-detail').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'}); }
}
async function refresh(newSession = false) {
  const version = ++state.version; state.busy = true; $('#refresh').disabled = true; $('#refresh').textContent = 'Loading…'; $('#staff-error').hidden = true;
  if (newSession) { state.token = null; state.orders = []; state.outbox = []; state.selected = null; $('#order-detail').hidden = true; }
  state.role = $('#preview-role').value; $('#role-description').textContent = descriptions[state.role];
  try {
    if (!state.token) { const session = await api('/preview/session',{method:'POST',body:JSON.stringify({role:state.role})}); if (version !== state.version) return; state.token = session.token; }
    const [orders,outbox] = await Promise.allSettled([api('/staff/orders'),api('/staff/outbox')]);
    if (version !== state.version) return;
    state.orders = orders.status === 'fulfilled' ? orders.value.orders || [] : [];
    state.outbox = outbox.status === 'fulfilled' ? outbox.value.items || [] : [];
    if (orders.status === 'rejected' && orders.reason.status !== 403) { $('#staff-error').textContent = orders.reason.message; $('#staff-error').hidden = false; }
    renderSummary(); renderOrders(); renderOutbox(outbox.status === 'rejected' ? outbox.reason : null);
    const selected = state.selected || new URL(location.href).searchParams.get('order');
    if (selected) renderDetail(selected,false);
    $('#announcer').textContent = `${state.orders.length} visible test orders loaded for ${$('#preview-role').selectedOptions[0].textContent}.`;
  } catch (error) { $('#staff-error').textContent = error.message; $('#staff-error').hidden = false; $('#orders-list').innerHTML = '<div class="empty-state">The local order register could not be loaded.</div>'; }
  finally { if (version === state.version) { state.busy = false; $('#refresh').disabled = false; $('#refresh').textContent = 'Refresh'; } }
}
async function refund() {
  if (state.busy || state.role !== 'owner' || !state.selected) return;
  const button = $('#staff-refund'); button.disabled = true; const id = state.selected;
  state.refundEvents[id] ||= crypto.randomUUID(); state.busy = true; $('#preview-role').disabled = true; $('#refresh').disabled = true;
  try { await api('/preview/payment',{method:'POST',body:JSON.stringify({order_id:id,event_id:state.refundEvents[id],outcome:'refund'})}); await refresh(); renderDetail(id,false); $('#announcer').textContent = 'Full refund simulated. Stock requires staff review.'; }
  catch(error) { await refresh(); const order = state.orders.find(order => order.id === id); renderDetail(id,false); if (order?.status !== 'refunded') { $('#detail-error').textContent = error.message + ' Retrying reuses the same test refund event.'; $('#detail-error').hidden = false; } }
  finally { state.busy = false; $('#preview-role').disabled = false; $('#refresh').disabled = false; if (button.isConnected) button.disabled = false; }
}
$('#preview-role').addEventListener('change',() => refresh(true));
$('#refresh').addEventListener('click',() => refresh());
$('#status-filter').addEventListener('change',renderOrders);
$('#close-detail').addEventListener('click',() => { $('#order-detail').hidden = true; const id = state.selected; state.selected = null; $(`[data-order="${CSS.escape(id || '')}"]`)?.focus(); });
document.addEventListener('click',(event) => { const order = event.target.closest('[data-order]'); if (order) renderDetail(order.dataset.order); if (event.target.closest('#staff-refund')) refund(); });
refresh(true);
