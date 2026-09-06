/* Progressive section navigation. No network, scroll hijacking, or hidden no-JS links.
 * Load deferred on all pages: --cw-header-height also supports the shared hero shell.
 * Context remains outside the sticky bar. Native anchors own URL/history changes. */
(function () {
  'use strict';
  var root = document.documentElement;
  var header = document.querySelector('.cw-hd');
  function measureHeader() {
    if (header) root.style.setProperty('--cw-header-height', header.getBoundingClientRect().height + 'px');
  }
  measureHeader();
  window.addEventListener('resize', measureHeader, {passive:true});
  if ('ResizeObserver' in window && header) new ResizeObserver(measureHeader).observe(header);

  var bar = document.querySelector('.cw-section-bar');
  if (!bar) return;
  var menu = bar.querySelector('details');
  var summary = menu.querySelector('summary');
  var current = menu.querySelector('.cw-section-current');
  var viewport = menu.querySelector('nav');
  var links = Array.prototype.slice.call(menu.querySelectorAll('.cw-section-links a'));
  var buttons = Array.prototype.slice.call(menu.querySelectorAll('[data-section-direction]'));
  var mobile = window.matchMedia('(max-width: 760px)');
  var targets = links.map(function (link) {
    try { return document.getElementById(decodeURIComponent(link.hash.slice(1))); }
    catch (_) { return null; }
  });
  var frame = 0, active = -1;
  function offset() {
    return (header ? header.getBoundingClientRect().height : 88) + bar.getBoundingClientRect().height + 12;
  }
  function overflow() {
    var overflowing = !mobile.matches && viewport.scrollWidth > viewport.clientWidth + 2;
    buttons.forEach(function (button) {
      button.hidden = !overflowing;
      button.disabled = Number(button.getAttribute('data-section-direction')) < 0
        ? viewport.scrollLeft <= 1
        : viewport.scrollLeft >= viewport.scrollWidth - viewport.clientWidth - 1;
    });
  }
  function select(index) {
    if (index < 0 || index === active) return;
    active = index;
    links.forEach(function (link, i) {
      if (i === index) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    current.textContent = links[index].textContent;
    if (!mobile.matches) {
      var item = links[index].getBoundingClientRect(), view = viewport.getBoundingClientRect();
      if (item.left < view.left) viewport.scrollLeft -= view.left - item.left;
      else if (item.right > view.right) viewport.scrollLeft += item.right - view.right;
    }
  }
  function update() {
    frame = 0;
    measureHeader();
    root.style.setProperty('--cw-section-bar-height', bar.getBoundingClientRect().height + 'px');
    var chosen = 0;
    var line = offset() + 10;
    targets.forEach(function (target, index) {
      if (target && target.getBoundingClientRect().top <= line) chosen = index;
    });
    // Cards in one grid row can share a heading position. Keep the visitor's
    // chosen destination current while that heading is at the reading edge.
    if (active >= 0 && targets[active]) {
      var activeTop = targets[active].getBoundingClientRect().top;
      if (activeTop >= line - 22 && activeTop <= line) chosen = active;
    }
    select(chosen);
    overflow();
  }
  function schedule() { if (!frame) frame = requestAnimationFrame(update); }
  function setMode() {
    menu.open = !mobile.matches;
    schedule();
  }
  function close() {
    if (!mobile.matches || !menu.open) return;
    menu.open = false;
    summary.focus({preventScroll:true});
  }
  menu.addEventListener('click', function (event) {
    var link = event.target.closest('.cw-section-links a');
    if (!link) return;
    select(links.indexOf(link));
    close(); // Close before the browser performs its native anchor jump.
  });
  menu.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && mobile.matches && menu.open) {
      event.preventDefault(); close();
    }
  });
  menu.addEventListener('toggle', schedule);
  buttons.forEach(function (button) {
    button.addEventListener('click', function () {
      viewport.scrollBy({left:Number(button.getAttribute('data-section-direction')) * Math.max(180, viewport.clientWidth * .7), behavior:'auto'});
    });
  });
  viewport.addEventListener('scroll', overflow, {passive:true});
  window.addEventListener('scroll', schedule, {passive:true});
  window.addEventListener('resize', schedule, {passive:true});
  window.addEventListener('hashchange', schedule);
  window.addEventListener('popstate', schedule);
  if (mobile.addEventListener) mobile.addEventListener('change', setMode);
  else mobile.addListener(setMode);
  if ('ResizeObserver' in window) new ResizeObserver(schedule).observe(bar);
  setMode();
  update();
  // Font loading can change the header height after an initial deep link lands.
  var initialHash = location.hash, interacted = false;
  ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach(function (name) {
    window.addEventListener(name, function () { interacted = true; }, {once:true, passive:true});
  });
  function alignInitialHash() {
    var target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (_) {}
    if (!interacted && initialHash && location.hash === initialHash && target) target.scrollIntoView({behavior:'instant', block:'start'});
    schedule();
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () {
    measureHeader(); requestAnimationFrame(alignInitialHash);
  });
})();
