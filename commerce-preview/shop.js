'use strict';

/* Local preview only. Customer details and access tokens stay in memory. Only
   product identifiers and quantities are remembered between page loads. */
const API = '/api/commerce';
const $ = (selector) => document.querySelector(selector);
const esc = (value = '') => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (paise) => new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(paise || 0) / 100);
const uuid = () => crypto.randomUUID();
const families = [
  {key:'prem_hw_gurjan',title:'Premium Hardwood',kicker:'Gurjan · BWR',description:'The proposed hardwood option for furniture and interior work.',image:'cwi-bwr-hardwood-plywood-960.webp',alt:'Hardwood-faced plywood panels with their layered edges visible'},
  {key:'prem_marine_gurjan',title:'Premium Marine',kicker:'Gurjan · BWP',description:'The proposed marine plywood option for demanding joinery requirements.',image:'cwi-marine-plywood-960.webp',alt:'Warm reddish plywood panels showing their grain and layered core'}
];
const state = {mode:'live',catalogue:null,cart:[],selected:{},quote:null,postcode:'',buyer:null,address:null,order:null,accessToken:null,staffToken:null,idempotencyKey:null,orderAttempt:null,orderRecovery:false,busy:false,loadVersion:0,revision:0,paymentEvents:{}};
const busyControls = new Map();
const recoveryControls = new Map();
const EDIT_CONTROLS = '[data-mode],[data-select-sku],[data-quantity-input],[data-quantity-action],[data-add],[data-remove],#delivery-postcode,#postcode-form button,#continue-checkout,#details-form input,#details-form button,#back-to-basket,#edit-details,#review-confirm';
function syncOrderRecoveryLock() {
  if (state.orderRecovery) {
    document.querySelectorAll(EDIT_CONTROLS).forEach(control => { if (!recoveryControls.has(control)) recoveryControls.set(control,control.disabled); control.disabled = true; });
  } else { recoveryControls.forEach((disabled,control) => { if (control.isConnected) control.disabled = disabled; }); recoveryControls.clear(); }
}
function setBusy(value) {
  state.busy = value;
  if (value) {
    document.querySelectorAll('[data-mode],[data-select-sku],[data-quantity-input],[data-quantity-action],[data-add],[data-remove],#delivery-postcode,#postcode-form button,#continue-checkout,#details-form input,#details-form button,#back-to-basket,#edit-details,#create-order,#review-confirm,[data-outcome],#new-order').forEach(control => { busyControls.set(control,control.disabled); control.disabled = true; });
  } else { busyControls.forEach((disabled,control) => { if (control.isConnected) control.disabled = disabled; }); busyControls.clear(); }
}
function captureSelection(postcode) { return {revision:state.revision,mode:state.mode,items:JSON.stringify(state.cart),postcode}; }
function selectionCurrent(snapshot) { return snapshot.revision === state.revision && snapshot.mode === state.mode && snapshot.items === JSON.stringify(state.cart) && snapshot.postcode === $('#delivery-postcode').value.trim(); }

async function api(path, options = {}) {
  let response;
  try { response = await fetch(API + path, {credentials:'same-origin',cache:'no-store',...options,headers:{'Content-Type':'application/json',...options.headers},signal:AbortSignal.timeout(15000)}); }
  catch { const error = new Error('The local preview could not be reached. Please keep the preview server running and try again.'); error.uncertain = true; throw error; }
  let data;
  try { data = await response.json(); } catch { const error = new Error('The preview returned an unreadable response. Please try again.'); error.uncertain = true; throw error; }
  if (!response.ok) { const error = new Error(data.error?.message || 'This action could not be completed. Please review the details and try again.'); error.code = data.error?.code; error.details = data.error?.details; error.status = response.status; error.uncertain = response.status >= 500; throw error; }
  return data;
}
function announce(text) { $('#announcer').textContent = ''; setTimeout(() => { $('#announcer').textContent = text; }, 40); }
function revealError(selector, message) { const element = $(selector); element.textContent = message; element.hidden = false; }
function clearError(selector) { $(selector).hidden = true; $(selector).textContent = ''; }
function getProduct(sku) { return state.catalogue?.products.find((product) => product.sku === sku); }
function familyFor(sku) { return families.find((family) => sku.startsWith(family.key)); }
function maxQuantity(product) { return Math.max(0, Math.min(product.max_quantity ?? 100, product.stock ?? product.stock_sheets ?? 100)); }
function quantityControl(sku, value, scope, disabled = false) {
  const product = getProduct(sku);
  const label = `${product?.name || sku}, ${product?.thickness_mm || ''} mm quantity`;
  return `<div class="quantity"><button type="button" data-quantity-action="minus" data-sku="${esc(sku)}" data-scope="${scope}" aria-label="Decrease ${esc(label)}" ${disabled ? 'disabled' : ''}>−</button><input type="number" min="${product?.min_quantity || 1}" max="${maxQuantity(product || {})}" step="1" value="${value}" data-quantity-input="${scope}" data-sku="${esc(sku)}" aria-label="${esc(label)}" ${disabled ? 'disabled' : ''}><button type="button" data-quantity-action="plus" data-sku="${esc(sku)}" data-scope="${scope}" aria-label="Increase ${esc(label)}" ${disabled ? 'disabled' : ''}>+</button></div>`;
}
function rememberCart() {
  try { localStorage.setItem(`cwi.preview.cart.${state.mode}`, JSON.stringify(state.cart.map(({sku, quantity}) => ({sku, quantity})))); } catch { /* Storage is optional. */ }
}
function restoreCart() {
  try {
    const values = JSON.parse(localStorage.getItem(`cwi.preview.cart.${state.mode}`) || '[]');
    const seen = new Set();
    state.cart = Array.isArray(values) ? values.filter((item) => item && typeof item.sku === 'string' && getProduct(item.sku) && Number.isInteger(item.quantity) && item.quantity > 0 && item.quantity <= maxQuantity(getProduct(item.sku)) && !seen.has(item.sku) && seen.add(item.sku)).map(({sku,quantity}) => ({sku,quantity})) : [];
  } catch { state.cart = []; }
}
function resetCheckout() {
  state.revision += 1;
  state.quote = null; state.idempotencyKey = null;
  $('#checkout').hidden = true;
  $('#details-stage').hidden = false; $('#review-stage').hidden = true; $('#payment-stage').hidden = true;
  $('#continue-checkout').disabled = true; $('#totals').innerHTML = '';
  $('#delivery-message').textContent = 'Check delivery again to confirm your updated total.'; $('#delivery-message').className = 'field-help';
  clearError('#basket-error');
}
function renderProducts() {
  $('#products').innerHTML = families.map((family) => {
    const variants = state.catalogue.products.filter((product) => product.sku.startsWith(family.key));
    if (!variants.length) return '';
    const product = variants.find((variant) => variant.sku === state.selected[family.key]) || variants[0];
    state.selected[family.key] = product.sku;
    const canBuy = state.mode === 'test' && state.catalogue.checkout_enabled && product.unit_price_paise != null && maxQuantity(product) > 0;
    return `<article class="product-card" data-family="${family.key}"><img class="product-image" src="/assets/photos/files/Plywood%20Product%20Photos/${family.image}" alt="${family.alt}" width="960" height="720"><p class="product-kicker">${family.kicker}</p><h3>${family.title}</h3><p class="product-description">${family.description}</p><div class="product-specs"><span>${esc(product.size || '8 × 4 ft')}</span><span>Per sheet</span></div><fieldset class="thickness-field"><legend>Choose thickness</legend><div class="thickness-options">${variants.map((variant) => `<button type="button" data-select-sku="${esc(variant.sku)}" data-family="${family.key}" aria-pressed="${variant.sku === product.sku}">${esc(variant.thickness_mm)} mm</button>`).join('')}</div></fieldset><div class="product-price">${product.unit_price_paise == null ? '<strong class="unapproved">Price awaiting approval</strong>' : `<strong>${money(product.unit_price_paise)}</strong><small>${state.mode === 'test' ? 'Test price / sheet' : 'Per sheet'}</small>`}</div><p class="stock-note">${state.mode === 'test' ? `${product.stock ?? product.stock_sheets ?? 0} test sheets available · ${product.min_quantity || 1}–${maxQuantity(product)} per order` : 'Stock and finished specifications await confirmation.'}</p><div class="buy-controls">${quantityControl(product.sku, product.min_quantity || 1, 'product', !canBuy)}<button type="button" class="button primary" data-add="${esc(product.sku)}" ${canBuy ? '' : 'disabled'}>${canBuy ? 'Add to selection <span aria-hidden="true">+</span>' : 'Purchasing not open'}</button></div></article>`;
  }).join('');
}
function renderBasket() {
  const totalQuantity = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  $('#basket-count').textContent = `${totalQuantity} ${totalQuantity === 1 ? 'sheet' : 'sheets'}`;
  $('#delivery-box').hidden = !state.cart.length;
  if (!state.cart.length) {
    $('#basket-items').innerHTML = '<div class="empty-basket"><span class="empty-symbol" aria-hidden="true">＋</span><strong>Start with the sheets you need.</strong><p>Add different materials or thicknesses to the same order.</p></div>';
    return;
  }
  $('#basket-items').innerHTML = state.cart.map((item) => {
    const product = getProduct(item.sku);
    const family = familyFor(item.sku);
    return `<div class="basket-item"><h3>${esc(family?.title || product.name)}</h3><p class="item-spec">${esc(product.size || '8 × 4 ft')} · ${esc(product.thickness_mm)} mm</p><div class="item-controls">${quantityControl(item.sku, item.quantity, 'basket')}<span class="item-total">${money(product.unit_price_paise * item.quantity)}</span></div><div class="item-footer"><span class="field-help">${money(product.unit_price_paise)} / test sheet</span><button type="button" class="remove" data-remove="${esc(item.sku)}" aria-label="Remove ${esc(product.name)} ${esc(product.thickness_mm)} mm">Remove</button></div></div>`;
  }).join('');
  if (state.quote) renderTotals();
}
function renderTotals() {
  const quote = state.quote;
  if (!quote) return;
  $('#totals').innerHTML = `<div class="totals"><div class="total-row"><span>Sheets</span><span>${money(quote.subtotal_paise)}</span></div><div class="total-row"><span>Delivery</span><span>${money(quote.shipping_paise)}</span></div><div class="total-row grand-total"><span>Test total</span><span>${money(quote.total_paise)}</span></div><p class="tax-note">${Number(quote.tax_paise) > 0 ? `${money(quote.tax_paise)} tax included` : 'Synthetic test amounts only'}</p></div>`;
}
function deliveryWindowText(quote) { const window = quote?.delivery_window; return window && Number.isFinite(window.min_days) && Number.isFinite(window.max_days) ? `Test delivery window: ${window.min_days}–${window.max_days} days.` : ''; }
async function loadCatalogue(mode) {
  if (state.orderRecovery) return;
  const version = ++state.loadVersion;
  state.mode = mode; state.order = null; state.buyer = null; state.address = null; state.postcode = ''; state.accessToken = null; state.paymentEvents = {};
  state.cart = []; state.catalogue = null; $('#products').innerHTML = '<p>Loading materials…</p>'; renderBasket();
  $('#details-form').reset(); $('#delivery-postcode').value = ''; $('#address-postcode').value = ''; resetCheckout();
  document.querySelectorAll('[data-mode]').forEach((button) => { button.setAttribute('aria-pressed', button.dataset.mode === mode ? 'true' : 'false'); button.disabled = true; });
  $('#mode-note').textContent = 'Loading the proposed catalogue…'; $('#mode-note').className = 'mode-note';
  try {
    const catalogue = await api(`/catalogue?mode=${mode}`);
    if (version !== state.loadVersion) return;
    state.catalogue = catalogue;
    if (!Array.isArray(catalogue.products)) throw new Error('The catalogue is unavailable. Please try again.');
    const deepLink = new URL(location.href).searchParams.get('sku');
    if (getProduct(deepLink)) { const family = familyFor(deepLink); if (family) state.selected[family.key] = deepLink; }
    restoreCart(); renderProducts(); renderBasket();
    if (mode === 'test') {
      $('#mode-note').className = 'mode-note is-test';
      $('#mode-note').innerHTML = '<strong>Test checkout:</strong> example prices and stock, no real payment. Use PIN <strong>683542</strong> or <strong>682001</strong> and made-up contact details. This does not represent an approved sale offer.';
    } else {
      $('#mode-note').innerHTML = '<strong>Online purchasing is not open.</strong> The selection is proposed; selling prices, stock, finished specifications and Kerala delivery terms need approval. Switch to Test checkout to review the full journey with synthetic examples.';
    }
    if (mode === 'test' && !catalogue.checkout_enabled) $('#mode-note').textContent += ' The test service is currently unavailable; please review the local configuration.';
    announce(mode === 'test' ? 'Test catalogue loaded. All amounts are synthetic.' : 'Actual catalogue setup loaded. Purchasing is blocked pending approval.');
  } catch (error) {
    $('#products').innerHTML = `<div class="form-errors">${esc(error.message)}<p><button type="button" class="text-button" id="retry-catalogue">Try again</button></p></div>`;
    $('#mode-note').textContent = 'The catalogue could not be loaded. Purchasing remains closed.';
    state.cart = []; renderBasket();
  } finally { if (version === state.loadVersion) document.querySelectorAll('[data-mode]').forEach((button) => { button.disabled = false; }); }
}
function updateCart(sku, quantity) {
  const product = getProduct(sku);
  if (!product || !Number.isInteger(quantity) || quantity < (product.min_quantity || 1) || quantity > maxQuantity(product)) {
    revealError('#basket-error', `Choose a whole number between ${product?.min_quantity || 1} and ${maxQuantity(product || {})} for this test item.`);
    announce($('#basket-error').textContent); return false;
  }
  const current = state.cart.find((item) => item.sku === sku);
  if (current) current.quantity = quantity; else state.cart.push({sku,quantity});
  resetCheckout(); rememberCart(); renderBasket(); return true;
}
function setStep(step) {
  document.querySelectorAll('[data-step]').forEach((element) => { if (element.dataset.step === step) element.setAttribute('aria-current','step'); else element.removeAttribute('aria-current'); });
  $('#details-stage').hidden = step !== 'details'; $('#review-stage').hidden = step !== 'review'; $('#payment-stage').hidden = step !== 'payment';
}
function focusSection(selector) { $(selector).focus({preventScroll:true}); $(selector).scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'}); }
async function checkDelivery(event) {
  event.preventDefault();
  clearError('#basket-error'); $('#delivery-postcode').removeAttribute('aria-invalid');
  const postcode = $('#delivery-postcode').value.trim();
  state.quote = null; $('#continue-checkout').disabled = true; $('#totals').innerHTML = ''; $('#checkout').hidden = true;
  if (!/^\d{6}$/.test(postcode)) {
    $('#delivery-message').textContent = 'Enter a six-digit Indian PIN code.'; $('#delivery-message').className = 'field-help error'; $('#delivery-postcode').setAttribute('aria-invalid','true'); $('#delivery-postcode').focus(); return;
  }
  const button = $('#postcode-form button'); button.disabled = true; button.textContent = 'Checking…';
  const snapshot = captureSelection(postcode);
  try {
    const result = await api('/quote', {method:'POST',body:JSON.stringify({mode:state.mode,items:state.cart,postcode})});
    if (!selectionCurrent(snapshot)) return;
    state.quote = result.quote; state.postcode = postcode; state.idempotencyKey = null;
    renderTotals(); $('#continue-checkout').disabled = false;
    $('#delivery-message').textContent = `Test delivery is available for ${postcode}. ${money(state.quote.shipping_paise)} delivery is included in your total. ${deliveryWindowText(state.quote)}`; $('#delivery-message').className = 'field-help success'; announce('Delivery checked. Your test total is ' + money(state.quote.total_paise));
  } catch (error) {
    if (!selectionCurrent(snapshot)) return;
    $('#delivery-message').textContent = error.message + ' Use 683542 or 682001 to try an eligible test delivery. Other delivery areas can be discussed with the quotation desk.'; $('#delivery-message').className = 'field-help error'; $('#delivery-postcode').setAttribute('aria-invalid','true');
  } finally { button.disabled = false; button.textContent = 'Check'; }
}
function validateDetails() {
  const fields = [
    ['buyer-name','Enter your full name.',(value) => value.length >= 2],
    ['buyer-phone','Enter a valid mobile number with 10–15 digits.',(value) => /^\+?[\d\s()-]{10,20}$/.test(value) && value.replace(/\D/g,'').length >= 10 && value.replace(/\D/g,'').length <= 15],
    ['buyer-email','Use a made-up address ending @example.invalid for this test.',(value) => /^[^\s@]+@example\.invalid$/.test(value)],
    ['buyer-gstin','Enter a 15-character GSTIN, or leave this optional field blank.',(value) => !value || /^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(value.toUpperCase())],
    ['address-line1','Enter the building and street.',(value) => value.length >= 4],
    ['address-city','Enter the delivery town or city.',(value) => value.length >= 2]
  ];
  const errors = [];
  for (const [id,message,valid] of fields) {
    const input = $('#' + id); const error = $('#' + id + '-error');
    input.removeAttribute('aria-invalid'); error.textContent = ''; input.setAttribute('aria-describedby',id + '-error');
    if (!valid(input.value.trim())) { input.setAttribute('aria-invalid','true'); error.textContent = message; errors.push({id,message}); }
  }
  if (errors.length) {
    $('#details-errors').innerHTML = `<strong>Please check ${errors.length} ${errors.length === 1 ? 'field' : 'fields'}.</strong><ul>${errors.map((error) => `<li><a href="#${error.id}">${esc(error.message)}</a></li>`).join('')}</ul>`; $('#details-errors').hidden = false; $('#details-errors').focus(); return false;
  }
  clearError('#details-errors'); return true;
}
function renderReview() {
  const quote = state.quote;
  $('#review-content').innerHTML = `<div class="review-address"><div><h3>Contact</h3><p>${esc(state.buyer.name)}</p><p>${esc(state.buyer.email)}</p><p>${esc(state.buyer.phone)}</p>${state.buyer.company ? `<p>${esc(state.buyer.company)}</p>` : ''}</div><div><h3>Delivery address</h3><p>${esc(state.address.line1)}</p>${state.address.line2 ? `<p>${esc(state.address.line2)}</p>` : ''}<p>${esc(state.address.city)}, Kerala ${esc(state.address.postcode)}</p></div></div><ul class="review-items">${quote.items.map((item) => `<li><span><strong>${esc(item.name)}</strong><span class="muted">${esc(getProduct(item.sku)?.thickness_mm)} mm · ${item.quantity} ${item.quantity === 1 ? 'sheet' : 'sheets'} × ${money(item.unit_price_paise)}</span></span><strong>${money(item.line_total_paise)}</strong></li>`).join('')}</ul><div class="totals"><div class="total-row"><span>Delivery</span><span>${money(quote.shipping_paise)}</span></div><div class="total-row grand-total"><span>Test order total</span><span>${money(quote.total_paise)}</span></div></div>`;
}
async function reviewDetails(event) {
  event.preventDefault(); if (!validateDetails() || !state.quote || state.busy) return;
  const snapshot = captureSelection(state.postcode); setBusy(true);
  try {
    const result = await api('/quote', {method:'POST',body:JSON.stringify({mode:state.mode,items:state.cart,postcode:state.postcode})});
    if (!selectionCurrent(snapshot)) return;
    state.quote = result.quote;
    state.buyer = {name:$('#buyer-name').value.trim(),email:$('#buyer-email').value.trim(),phone:$('#buyer-phone').value.trim(),company:$('#buyer-company').value.trim(),gstin:$('#buyer-gstin').value.trim().toUpperCase()};
    state.address = {line1:$('#address-line1').value.trim(),line2:$('#address-line2').value.trim(),city:$('#address-city').value.trim(),state:'Kerala',postcode:state.postcode};
    state.idempotencyKey = null; $('#review-confirm').checked = false; clearError('#order-error'); renderReview();
    if (state.buyer.gstin) { const line = document.createElement('p'); line.textContent = 'GSTIN: ' + state.buyer.gstin; $('#review-content .review-address>div').append(line); }
    if (deliveryWindowText(state.quote)) { const line = document.createElement('p'); line.className = 'read-only-note'; line.textContent = deliveryWindowText(state.quote); $('#review-content').append(line); }
    renderTotals(); setStep('review'); focusSection('#review-title');
  } catch (error) { if (selectionCurrent(snapshot)) { revealError('#details-errors',error.message); $('#details-errors').focus(); } }
  finally { setBusy(false); }
}
function orderId(order = state.order) { return order?.id || order?.order_id || ''; }
function orderStatus(order = state.order) { return order?.status || order?.payment_status || 'pending_payment'; }
function statusKind(status) { if (/refund/.test(status)) return 'refunded'; if (/^(paid|confirmed|payment_confirmed|ready_for_fulfilment)$/.test(status)) return 'paid'; if (/fail|cancel|expire/.test(status)) return 'failed'; return 'pending'; }
function statusLabel(status) { return String(status).replaceAll('_',' ').replace(/^./,c => c.toUpperCase()); }
function renderPayment() {
  const order = state.order; const status = orderStatus(order); const kind = statusKind(status); const id = orderId(order); const total = order.total_paise ?? order.quote?.total_paise ?? order.totals?.total_paise ?? state.quote?.total_paise;
  const descriptions = {pending:'The test order is saved and stock is reserved. Choose a simulated outcome below.',paid:'The backend has recorded the simulated payment. The test order and its notification outbox can now be reviewed by staff.',failed:'The unsuccessful payment outcome is recorded. The test order remains traceable; no goods are released.',refunded:'The simulated refund is recorded. No real money has moved. Paid sheets require staff stock review and are not automatically returned to available stock.'};
  $('#payment-content').innerHTML = `<div class="payment-heading"><span class="payment-symbol" aria-hidden="true">${kind === 'paid' || kind === 'refunded' ? '✓' : '↗'}</span><div><h2 id="payment-title" tabindex="-1">${kind === 'paid' ? 'Your test order is paid.' : kind === 'refunded' ? 'Test refund recorded.' : kind === 'failed' ? 'Test payment closed.' : 'Your test order is recorded.'}</h2><p>${esc(id)}</p></div></div><div class="receipt-lines"><div><span>Order status</span><strong>${esc(statusLabel(status))}</strong></div><div><span>Test total</span><strong>${money(total)}</strong></div></div><p class="payment-status">${descriptions[kind]}</p><div id="payment-error" class="form-errors" role="alert" hidden></div>${kind === 'pending' ? '<div class="payment-options"><h3>Simulate a payment outcome</h3><p>This exercises local order handling only. No UPI ID, PIN, bank account or payment link is used.</p><div class="payment-buttons"><button type="button" class="button primary" data-outcome="success">Simulate success ✓</button><button type="button" class="button secondary" data-outcome="failure">Simulate failure</button><button type="button" class="button secondary" data-outcome="cancel">Simulate cancellation</button><button type="button" class="button secondary" data-outcome="expire">Expire reservation</button></div></div>' : ''}<div class="detail-actions"><a class="button secondary" href="/commerce-preview/staff.html?order=${encodeURIComponent(id)}">Review in staff preview <span aria-hidden="true">↗</span></a>${kind === 'paid' ? '<button type="button" class="text-button" data-outcome="refund">Simulate full refund</button>' : ''}</div><button id="new-order" class="text-button next-order" type="button">Start another test order <span aria-hidden="true">→</span></button>`;
}
async function createOrder() {
  if (state.busy || state.order) return;
  clearError('#order-error');
  if (!$('#review-confirm').checked) { revealError('#order-error','Confirm that this is a simulated order before continuing.'); $('#review-confirm').focus(); return; }
  if (state.mode !== 'test' || !state.quote || !state.buyer || !state.address) { revealError('#order-error','Return to your selection and check delivery before creating a test order.'); return; }
  setBusy(true); const button = $('#create-order'); button.textContent = 'Recording test order…';
  state.orderAttempt ||= {key:state.idempotencyKey || uuid(),body:JSON.stringify({mode:'test',items:state.cart,postcode:state.postcode,buyer:state.buyer,address:state.address,expected_catalogue_fingerprint:state.quote.catalogue_fingerprint})};
  state.idempotencyKey = state.orderAttempt.key;
  try {
    const result = await api('/orders',{method:'POST',headers:{'Idempotency-Key':state.orderAttempt.key},body:state.orderAttempt.body});
    state.order = result.order; state.accessToken = result.access_token;
    state.orderAttempt = null; state.orderRecovery = false;
    state.cart = []; rememberCart(); renderBasket();
    renderPayment(); setStep('payment'); focusSection('#payment-title'); announce('Test order recorded. No real payment has been taken.');
  } catch (error) {
    state.orderRecovery = error.uncertain === true;
    if (!state.orderRecovery) { state.orderAttempt = null; state.idempotencyKey = null; }
    revealError('#order-error',state.orderRecovery ? 'The order result was not confirmed. Your submitted selection is held here. Recover the same test order before editing or starting another; this will not create another reservation.' : error.message);
  }
  finally { setBusy(false); syncOrderRecoveryLock(); button.innerHTML = state.orderRecovery ? 'Recover saved test order <span aria-hidden="true">→</span>' : 'Create test order <span aria-hidden="true">→</span>'; }
}
async function simulate(outcome) {
  if (state.busy || !state.order || state.mode !== 'test') return;
  setBusy(true); clearError('#payment-error');
  const previousStatus = orderStatus();
  const eventKey = `${orderId()}:${outcome}`;
  state.paymentEvents[eventKey] ||= uuid();
  try {
    if (!state.staffToken) { const session = await api('/preview/session',{method:'POST',body:JSON.stringify({role:'owner'})}); state.staffToken = session.token; }
    const result = await api('/preview/payment',{method:'POST',headers:{Authorization:`Bearer ${state.staffToken}`},body:JSON.stringify({order_id:orderId(),event_id:state.paymentEvents[eventKey],outcome})});
    if (result.order) state.order = result.order;
    else { const refreshed = await api(`/orders/${encodeURIComponent(orderId())}`,{headers:{Authorization:`Bearer ${state.accessToken}`}}); state.order = refreshed.order; }
    renderPayment(); focusSection('#payment-title'); announce('Simulated payment status updated to ' + statusLabel(orderStatus()));
  } catch (error) {
    try { const refreshed = await api(`/orders/${encodeURIComponent(orderId())}`,{headers:{Authorization:`Bearer ${state.accessToken}`}}); state.order = refreshed.order; renderPayment(); if (orderStatus() !== previousStatus) announce('The latest order status was recovered: ' + statusLabel(orderStatus())); else revealError('#payment-error',error.message + ' Retrying the same outcome reuses the original test event.'); }
    catch { revealError('#payment-error','The payment result could not be confirmed. Retry the same outcome to safely reuse the original test event, or inspect the order in staff review.'); }
  }
  finally { setBusy(false); }
}

document.addEventListener('click',(event) => {
  if (state.busy) return;
  const mode = event.target.closest('[data-mode]'); if (mode && !mode.disabled && mode.dataset.mode !== state.mode) loadCatalogue(mode.dataset.mode);
  const select = event.target.closest('[data-select-sku]'); if (select) { state.selected[select.dataset.family] = select.dataset.selectSku; renderProducts(); $(`[data-select-sku="${CSS.escape(select.dataset.selectSku)}"]`).focus(); }
  const quantity = event.target.closest('[data-quantity-action]');
  if (quantity && !quantity.disabled) { const {sku,scope,quantityAction} = quantity.dataset; const input = quantity.parentElement.querySelector('input'); const value = Number(input.value) + (quantityAction === 'plus' ? 1 : -1); const product = getProduct(sku); if (value >= (product?.min_quantity || 1) && value <= maxQuantity(product || {})) { if (scope === 'basket') { updateCart(sku,value); $(`[data-quantity-action="${quantityAction}"][data-scope="basket"][data-sku="${CSS.escape(sku)}"]`)?.focus(); } else input.value = value; } else announce(`Choose between ${product?.min_quantity || 1} and ${maxQuantity(product || {})} sheets.`); }
  const add = event.target.closest('[data-add]');
  if (add && !add.disabled) { const sku = add.dataset.add; const quantity = Number(add.closest('.buy-controls').querySelector('input').value); const current = state.cart.find(item => item.sku === sku)?.quantity || 0; if (updateCart(sku,current + quantity)) { announce(`${quantity} ${getProduct(sku).name} sheets added to your selection.`); const label = add.innerHTML; add.textContent = 'Added ✓'; setTimeout(() => { if (add.isConnected) add.innerHTML = label; },900); } }
  const remove = event.target.closest('[data-remove]'); if (remove) { state.cart = state.cart.filter(item => item.sku !== remove.dataset.remove); resetCheckout(); rememberCart(); renderBasket(); announce('Item removed from your selection.'); $('#basket-title').setAttribute('tabindex','-1'); $('#basket-title').focus(); }
  const outcome = event.target.closest('[data-outcome]'); if (outcome) simulate(outcome.dataset.outcome);
  if (event.target.closest('#new-order')) { loadCatalogue('test').then(() => { $('#catalogue-title').setAttribute('tabindex','-1'); focusSection('#catalogue-title'); }); }
  if (event.target.closest('#retry-catalogue')) loadCatalogue(state.mode);
});
document.addEventListener('change',(event) => {
  if (event.target.matches('[data-quantity-input="basket"]')) { const sku = event.target.dataset.sku; if (!updateCart(sku,Number(event.target.value))) renderBasket(); else $(`[data-quantity-input="basket"][data-sku="${CSS.escape(sku)}"]`)?.focus(); }
});
$('#postcode-form').addEventListener('submit',checkDelivery);
$('#delivery-postcode').addEventListener('input',() => resetCheckout());
$('#continue-checkout').addEventListener('click',() => { if (!state.quote) return; $('#address-postcode').value = state.postcode; $('#checkout').hidden = false; setStep('details'); focusSection('#checkout-title'); });
$('#back-to-basket').addEventListener('click',() => { $('#checkout').hidden = true; $('#delivery-postcode').focus(); $('#basket').scrollIntoView({block:'start'}); });
$('#edit-details').addEventListener('click',() => { setStep('details'); focusSection('#checkout-title'); });
$('#details-form').addEventListener('submit',reviewDetails);
$('#fill-test-details').addEventListener('click',() => { if (state.mode !== 'test') return; const sample = {'buyer-name':'Preview Customer','buyer-phone':'9000000000','buyer-email':'preview@example.invalid','buyer-company':'Example Test Company','address-line1':'Test Building 1, Example Street','address-line2':'Preview address only','address-city':'Perumbavoor'}; Object.entries(sample).forEach(([id,value]) => { $('#' + id).value = value; }); announce('Made-up example details filled.'); });
$('#create-order').addEventListener('click',createOrder);
loadCatalogue('live');
