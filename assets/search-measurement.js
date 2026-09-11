/* Optional Google measurement. The quote form and first-party accepted-enquiry
 * counters operate independently. Never send form values, search text or URL queries. */
(function () {
  'use strict';
  var ID = 'G-QD4G3EYG2G', CONTAINER = 'GTM-K2DJRFM8';
  var KEY = 'cwi_analytics_choice_v1', MAX_AGE = 180 * 86400000;
  var production = /^(www\.)?cochinwood\.in$/.test(location.hostname);
  var banner = document.getElementById('cwi-privacy');
  var settings = document.querySelector('[data-cwi-privacy-open]');
  if (!banner || !settings) return;
  var choice = null, loaded = false, pageSent = false;
  var allowed = {quote_click:'quote_click', tel_click:'contact_phone', whatsapp_click:'contact_whatsapp',
    form_view:'quote_form_view', form_start:'quote_form_start', form_validation_error:'quote_validation_error'};
  var products = ['packing-plywood','okoume-plywood','rubberwood-plywood','commercial-plywood','marine-plywood',
    'bwr-hardwood-plywood','film-faced-shuttering-plywood','container-flooring-plywood','block-board-flush-doors',
    'chequered-anti-skid-plywood','finger-joint-board','particle-board','plywood-boxes-crates','plywood-pallets',
    'plywood-cable-drums','sawn-timber'];
  function path(value) {
    return typeof value === 'string' && /^\/(?:[a-z0-9-]+\/)*[a-z0-9-]*$/.test(value) ? value : '/';
  }
  var current = path(location.pathname.replace(/\.html$/, ''));
  var pageLocation = 'https://www.cochinwood.in' + current;
  var referrer = '';
  try { if (document.referrer) referrer = new URL(document.referrer).origin; } catch (_) {}
  function command() { window.dataLayer.push(arguments); }
  function initializeQueue() {
    window.dataLayer = window.dataLayer || [];
    command('consent', 'default', {analytics_storage:'denied', ad_storage:'denied',
      ad_user_data:'denied', ad_personalization:'denied', functionality_storage:'granted', security_storage:'granted'});
    command('set', {page_location:pageLocation, page_referrer:referrer,
      send_page_view:false, allow_google_signals:false, allow_ad_personalization_signals:false,
      ads_data_redaction:true, url_passthrough:false});
  }
  function event(name, details) {
    if (choice !== 'accepted' || !production) return;
    command('event', name, Object.assign({send_to:ID, page_location:pageLocation,
      page_referrer:referrer, page_title:document.title}, details || {}));
  }
  function activate() {
    if (!production) return;
    window['ga-disable-' + ID] = false;
    if (!loaded) {
      initializeQueue();
      command('consent','update',{analytics_storage:'granted', ad_storage:'denied', ad_user_data:'denied', ad_personalization:'denied'});
      window.dataLayer.push({'gtm.start':Date.now(), event:'gtm.js'});
      window.dataLayer.push({event:'cwi_analytics_ready'});
      var script = document.createElement('script');
      script.async = true;
      script.src = 'https://www.googletagmanager.com/gtm.js?id=' + CONTAINER;
      document.head.appendChild(script);
      loaded = true;
    } else command('consent','update',{analytics_storage:'granted'});
    if (!pageSent) {
      event('page_view'); pageSent = true;
      if (products.indexOf(current.slice(1)) !== -1) event('view_item',{items:[{item_id:current.slice(1)}]});
      if (current === '/contact' && !/[?&]sent=1(?:&|$)/.test(location.search)) event('quote_form_view');
    }
  }
  function clearCookies() {
    document.cookie.split(';').forEach(function (part) {
      var name = part.split('=')[0].trim();
      if (!/^(_ga(?:_|$)|_gid$|_gat(?:_|$))/.test(name)) return;
      ['', '; domain=' + location.hostname, '; domain=.cochinwood.in'].forEach(function (domain) {
        document.cookie = name + '=; Max-Age=0; path=/' + domain + '; SameSite=Lax; Secure';
      });
    });
  }
  function save(value) {
    choice = value;
    try { localStorage.setItem(KEY, JSON.stringify({value:value, saved:Date.now()})); } catch (_) {}
    banner.hidden = true;
    settings.setAttribute('aria-expanded','false');
    if (value === 'accepted') activate();
    else {
      window['ga-disable-' + ID] = true;
      if (loaded) command('consent','update',{analytics_storage:'denied', ad_storage:'denied', ad_user_data:'denied', ad_personalization:'denied'});
      clearCookies();
    }
    settings.focus({preventScroll:true});
  }
  window.cwiAnalytics = {track:function (name, source) {
    if (!allowed[name] || name === 'form_view') return; // The current view is emitted once on consent.
    event(allowed[name], {source_page:path(source)});
  }};
  settings.hidden = false;
  settings.addEventListener('click',function () {
    banner.hidden = false;
    settings.setAttribute('aria-expanded','true');
    banner.querySelector('[data-cwi-consent="denied"]').focus({preventScroll:true});
  });
  banner.querySelectorAll('[data-cwi-consent]').forEach(function (button) {
    button.addEventListener('click',function () { save(button.getAttribute('data-cwi-consent')); });
  });
  banner.addEventListener('keydown',function (e) { if (e.key === 'Escape') { save(choice || 'denied'); } });
  try {
    var saved = JSON.parse(localStorage.getItem(KEY));
    if (saved && ['accepted','denied'].indexOf(saved.value) !== -1 && Number.isFinite(saved.saved)
      && Date.now() >= saved.saved && Date.now() - saved.saved < MAX_AGE) choice = saved.value;
  } catch (_) {}
  if (choice === 'accepted') activate();
  else if (choice === null) { banner.hidden = false; settings.setAttribute('aria-expanded','true'); }
})();
