/* Per-product RFQs; native POST keeps the existing verified server handoff. */
(function () {
  'use strict';
  var form = document.getElementById('cwq2-form');
  if (!form) return;
  var params = new URLSearchParams(location.search);
  var draftKey = 'cwq_draft_v2', retryStore = 'cwq_retry', loadedAt = Date.now();
  var host = document.getElementById('cwq-items'), template = document.getElementById('cwq-item-template');
  var add = document.getElementById('cwq-add-item'), status = document.getElementById('cwq-item-status');
  var error = document.getElementById('cwq2-error'), nextId = 2, retryKey = '', submittedSignature = '', sourcePage = '';
  var maxItems = Number(form.dataset.maxItems) || 20;
  var fields = ['product','grade','thickness','dimensions','quantity','unit','help_me_choose'];
  var shared = ['name','company','email','phone','destination','incoterm','description'];
  var presets = {
    'packing-plywood':'Packing Plywood','commercial-plywood':'Commercial Plywood',
    'okoume-plywood':'Okoume Plywood','rubberwood-plywood':'Rubberwood Plywood',
    'film-faced-shuttering-plywood':'Film Faced/Shuttering','marine-plywood':'BWP Marine Plywood - IS 710',
    'bwr-hardwood-plywood':'BWR Hardwood Plywood - IS 303','container-flooring-plywood':'Container Flooring',
    'block-board-flush-doors':'Block Board/Flush Door','plywood-boxes-crates':'Wooden/Plywood Packing Case',
    'plywood-pallets':'Plywood Pallets','sawn-timber':'Timber/Runners/Planks',
    'chequered-anti-skid-plywood':'Chequered Anti-Skid Plywood','finger-joint-board':'Finger-Joint Board',
    'particle-board':'Particle Board','plywood-cable-drums':'Plywood Cable Drums',
    'premium-hardwood-plywood':'Premium Hardwood Plywood'
  };
  function rows() { return Array.from(host.querySelectorAll('[data-quote-item]')); }
  function value(name) { return form.elements[name].value.trim(); }
  function itemValue(row) {
    var item = {};
    fields.forEach(function (key) {
      var field = row.querySelector('[data-item-field="'+key+'"]');
      item[key] = key === 'help_me_choose' ? field.checked : field.value.trim();
    });
    item.help_me_choose = item.help_me_choose || item.product === 'Help me choose';
    return item;
  }
  function setItem(row, item) {
    fields.forEach(function (key) {
      var field = row.querySelector('[data-item-field="'+key+'"]');
      if (key === 'help_me_choose') field.checked = item[key] === true;
      else field.value = typeof item[key] === 'string' ? item[key] : '';
    });
  }
  function renumber() {
    var all = rows();
    all.forEach(function (row, i) {
      row.querySelector('[data-item-number]').textContent = i + 1;
      var remove = row.querySelector('[data-remove-item]');
      remove.hidden = all.length === 1;
      remove.setAttribute('aria-label','Remove product '+(i+1));
      row.querySelector('[data-item-field="product"]').required = !row.querySelector('[data-item-field="help_me_choose"]').checked;
    });
    add.disabled = all.length >= maxItems;
  }
  function newItem(item, focus) {
    if (rows().length >= maxItems) return;
    var holder = document.createElement('template');
    holder.innerHTML = template.innerHTML.replaceAll('__INDEX__', String(nextId++));
    var row = holder.content.firstElementChild;
    if (item) setItem(row,item);
    host.append(row); renumber();
    if (focus) row.querySelector('[data-item-field="product"]').focus();
  }
  function saveDraft() {
    var common = {};
    shared.forEach(function (key) { common[key] = value(key); });
    try { sessionStorage.setItem(draftKey, JSON.stringify({at:Date.now(),items:rows().map(itemValue),shared:common,retry:retryKey,submittedSignature:submittedSignature,sourcePage:sourcePage})); }
    catch (_) { /* Browser Back still retains the live controls when storage is unavailable. */ }
  }
  function showError(message) {
    error.textContent = message; error.style.display = 'block';
    error.scrollIntoView({block:'center',behavior:'auto'});
  }
  var unconfirmedReturn = params.get('sent') === '1';
  var received = params.get('received') || '', pendingDraft = null;
  try { pendingDraft = JSON.parse(sessionStorage.getItem(draftKey) || 'null'); } catch (_) {}
  var acceptedReturn = unconfirmedReturn && /^[A-Za-z0-9_-]{16,100}$/.test(received) &&
    (!pendingDraft || (pendingDraft.retry === received && pendingDraft.submittedSignature));
  if (acceptedReturn) {
    try { sessionStorage.removeItem(draftKey); sessionStorage.removeItem(retryStore); } catch (_) {}
    form.innerHTML = '<div class="cw-form__ok" aria-live="polite"><h2>Request received.</h2><p>Our sales desk replies within one business day. In a hurry?</p><a class="cw-btn cw-btn--p" href="https://wa.me/919567410175">Message the desk on WhatsApp</a></div>';
    document.getElementById('quote').scrollIntoView();
    return;
  }
  var restored = false;
  try {
    retryKey = sessionStorage.getItem(retryStore) || '';
    var saved = JSON.parse(sessionStorage.getItem(draftKey) || 'null');
    if (saved && Number.isFinite(saved.at) && Date.now()-saved.at >= 0 && Date.now()-saved.at < 4*60*60*1000 && Array.isArray(saved.items) && saved.items.length && saved.items.length <= maxItems && saved.items.every(function(item){return item && typeof item==='object' && !Array.isArray(item);}) && saved.shared) {
      setItem(rows()[0],saved.items[0]);
      saved.items.slice(1).forEach(function (item) { newItem(item,false); });
      shared.forEach(function (key) { if (typeof saved.shared[key] === 'string') form.elements[key].value = saved.shared[key]; });
      retryKey = saved.retry || retryKey; restored = true;
      submittedSignature = typeof saved.submittedSignature === 'string' ? saved.submittedSignature : '';
      sourcePage = typeof saved.sourcePage === 'string' ? saved.sourcePage : '';
    } else {
      sessionStorage.removeItem(draftKey); sessionStorage.removeItem(retryStore); retryKey='';
    }
  } catch (_) {}
  function freshRetryKey() { return window.crypto && crypto.randomUUID ? crypto.randomUUID() : 'enquiry-'+Date.now()+'-'+Math.random().toString(36).slice(2); }
  if (!restored || !submittedSignature || !/^[A-Za-z0-9_-]{16,100}$/.test(retryKey)) retryKey = freshRetryKey();
  form.elements.enquiry_id.value = retryKey;
  if (!sourcePage) {
    sourcePage = presets[params.get('product')] ? '/'+params.get('product') : location.pathname;
    try { sourcePage = sessionStorage.getItem('cwq_from') || sourcePage; } catch (_) {}
  }
  if (!restored && presets[params.get('product')]) rows()[0].querySelector('[data-item-field="product"]').value = presets[params.get('product')];
  renumber(); add.hidden = false;
  if (restored) status.textContent = 'Your unsent enquiry has been restored in this tab.';
  if (unconfirmedReturn) showError('We could not confirm that this enquiry was received. Your entries have been kept. Please complete verification and try again, or contact our sales desk.');
  add.addEventListener('click',function () {
    newItem(null,true); status.textContent = 'Product '+rows().length+' added. Add its own specification and quantity.'; saveDraft();
  });
  host.addEventListener('click',function (event) {
    var button = event.target.closest('[data-remove-item]');
    if (!button || rows().length <= 1) return;
    var row = button.closest('[data-quote-item]'), all = rows(), index = all.indexOf(row);
    row.remove(); renumber();
    var next = rows()[Math.min(index,rows().length-1)];
    next.querySelector('[data-item-field="product"]').focus();
    status.textContent = 'Product removed. '+rows().length+' product'+(rows().length===1?'':'s')+' in this enquiry.'; saveDraft();
  });
  form.addEventListener('input',function (event) { event.target.setCustomValidity && event.target.setCustomValidity(''); renumber(); saveDraft(); });
  form.addEventListener('change',function () { renumber(); saveDraft(); });
  window.addEventListener('pageshow',function (event) {
    renumber();
    // Returning to a previously successful form via the back-forward cache is a new enquiry.
    try { if (event.persisted && submittedSignature && !sessionStorage.getItem(retryStore)) { retryKey=freshRetryKey(); submittedSignature=''; } } catch (_) {}
  });
  form.addEventListener('submit',function (event) {
    error.textContent = ''; error.style.display = 'none';
    saveDraft();
    if (value('cwq2_website') || Date.now()-loadedAt < 3000) {
      event.preventDefault(); showError('Please review your details and try again.'); return;
    }
    var items = rows().map(itemValue);
    for (var i=0;i<items.length;i++) {
      var item = items[i];
      if (!item.product && !item.help_me_choose) {
        event.preventDefault(); showError('Choose a product or select “Help me choose” for product '+(i+1)+'.'); return;
      }
      if (item.quantity && (!/^\d+(?:\.\d+)?$/.test(item.quantity) || Number(item.quantity) <= 0)) {
        event.preventDefault();
        var qty = rows()[i].querySelector('[data-item-field="quantity"]');
        qty.setCustomValidity('Enter a quantity greater than zero, or leave it empty if not known.'); qty.reportValidity(); return;
      }
    }
    var token = form.querySelector('[name="cf-turnstile-response"]');
    if (!token || !token.value) {
      event.preventDefault();
      error.innerHTML = 'Verification has not finished, so this cannot be sent yet. Give it a moment and try again — or contact the sales desk on <a href="https://wa.me/919567410175">WhatsApp</a> or <a href="mailto:sales@cochinwood.in">sales@cochinwood.in</a>. Your product entries are unchanged.';
      error.style.display = 'block'; error.scrollIntoView({block:'center',behavior:'auto'}); return;
    }
    form.elements.enquiry.value = JSON.stringify({version:2,items:items,destination:value('destination'),incoterm:value('incoterm'),source_page:sourcePage,original_text:value('description')});
    form.elements.spec_grade.value = [items[0].thickness,items[0].grade].filter(Boolean).join(' ');
    var signature = JSON.stringify({enquiry:form.elements.enquiry.value,name:value('name'),company:value('company'),email:value('email'),phone:value('phone')});
    // An identical retry keeps its key. Changed items/contact details must not replay older data.
    if (submittedSignature && submittedSignature !== signature) retryKey = freshRetryKey();
    form.elements.enquiry_id.value = retryKey;
    // Native URL-encoded forms normalize textarea line endings to CRLF before encoding.
    var encodedFields = new URLSearchParams();
    new FormData(form).forEach(function (entry,key) {
      encodedFields.append(key.replace(/\r\n|\r|\n/g,'\r\n'),String(entry).replace(/\r\n|\r|\n/g,'\r\n'));
    });
    var body = encodedFields.toString();
    if (new TextEncoder().encode(body).length > 30000) {
      event.preventDefault(); showError('This enquiry is too long to send in one request. Shorten the notes or split the products into two enquiries. Your entries have been kept.'); return;
    }
    submittedSignature = signature;
    saveDraft();
    try { sessionStorage.setItem(retryStore,retryKey); } catch (_) {}
  });
})();
