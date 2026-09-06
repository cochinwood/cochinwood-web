/* Cochin Wood: progressive motion only. Content is visible without this script.
   Integrate deferred after the site script and append experience-motion.css to the bundle.
   data-reveal[="image"], data-delay="0..180" (ms), data-parallax on an image inside
   a clipped wrapper; process-step/image attributes share a nonempty string ID.
   Process state adds is-active / data-process-active; CSS never hides other content. */
(function () {
  'use strict';
  var observers = [], frame = 0, listening = false;
  var reduce = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var connection = navigator.connection;
  var reveals = [], images = [], steps = [], panels = [], headers = [];
  function limited() { return !!((reduce && reduce.matches) || (connection && connection.saveData)); }
  function reset() {
    observers.forEach(function (o) { o.disconnect(); }); observers = [];
    if (frame) { cancelAnimationFrame(frame); frame = 0; }
    if (listening) {
      window.removeEventListener('scroll', requestFrame);
      window.removeEventListener('resize', requestFrame); listening = false;
    }
    reveals.forEach(function (el) { el.classList.remove('cw-reveal-enter'); });
    images.forEach(function (el) { el.style.removeProperty('--cw-parallax-y'); });
    panels.forEach(function (el) { el.classList.remove('is-active'); el.removeAttribute('data-process-active'); });
    headers.forEach(function (el) { el.classList.remove('is-scrolled'); });
  }
  function update() {
    frame = 0;
    if (limited()) { reset(); return; }
    try {
      var height = window.innerHeight || document.documentElement.clientHeight;
      headers.forEach(function (el) { el.classList.toggle('is-scrolled', window.scrollY > 24); });
      images.forEach(function (el) {
        var parent = el.parentElement;
        if (!parent) return;
        var rect = parent.getBoundingClientRect();
        if (rect.bottom < -80 || rect.top > height + 80) return;
        var offset = Math.max(-14, Math.min(14, ((rect.top + rect.height / 2) / height - .5) * -28));
        el.style.setProperty('--cw-parallax-y', offset.toFixed(2) + 'px');
      });
    } catch (_) { reset(); }
  }
  function requestFrame() {
    if (!frame && !document.hidden) frame = requestAnimationFrame(update);
  }
  function activate(id) {
    if (!id || !panels.some(function (p) { return p.getAttribute('data-process-image') === id; })) return;
    panels.forEach(function (p) {
      var active = p.getAttribute('data-process-image') === id;
      p.classList.toggle('is-active', active);
      p.setAttribute('data-process-active', active ? 'true' : 'false');
    });
  }
  function start() {
    reset();
    if (limited() || !('IntersectionObserver' in window)) return;
    try {
      var height = window.innerHeight || document.documentElement.clientHeight;
      var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var el = entry.target;
          // Never replay or initially conceal content; only animate new below-fold arrivals.
          revealObserver.unobserve(el);
          if (el.getAttribute('data-revealed') === 'true') return;
          el.setAttribute('data-revealed', 'true');
          var delay = Number(el.getAttribute('data-delay')) || 0;
          el.style.setProperty('--cw-reveal-delay', Math.max(0, Math.min(180, delay)) + 'ms');
          el.classList.add('cw-reveal-enter');
        });
      }, {threshold: .08});
      observers.push(revealObserver);
      reveals.forEach(function (el) {
        if (el.getBoundingClientRect().top < height) el.setAttribute('data-revealed', 'true');
        else revealObserver.observe(el);
      });
      if (steps.length && panels.length) {
        var visible = new Map();
        var processObserver = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) visible.set(entry.target, entry.intersectionRatio);
            else visible.delete(entry.target);
          });
          var best = null, score = -1;
          visible.forEach(function (ratio, el) { if (ratio > score) { best = el; score = ratio; } });
          if (best) activate(best.getAttribute('data-process-step'));
        }, {rootMargin:'-20% 0px -30% 0px', threshold:[0,.1,.25,.5,.75,1]});
        observers.push(processObserver);
        steps.forEach(function (el) { processObserver.observe(el); });
      }
      if (images.length || headers.length) {
        window.addEventListener('scroll', requestFrame, {passive:true});
        window.addEventListener('resize', requestFrame, {passive:true});
        listening = true; requestFrame();
      }
    } catch (_) { reset(); }
  }
  function init() {
    // Bring the shared page families into the same motion language. Their
    // original content remains fully visible before this optional enhancement.
    document.querySelectorAll('.cwp__hero-img,.cwp__gallery-item,.cwsec-image,.cwr__card,.cw-section__head,.cw-story__media').forEach(function (el) {
      if (!el.hasAttribute('data-reveal')) el.setAttribute('data-reveal', 'image');
    });
    reveals = Array.from(document.querySelectorAll('[data-reveal]'));
    images = Array.from(document.querySelectorAll('img[data-parallax]'));
    steps = Array.from(document.querySelectorAll('[data-process-step]'));
    panels = Array.from(document.querySelectorAll('[data-process-image]'));
    headers = Array.from(document.querySelectorAll('.cw-header'));
    start();
    if (reduce && reduce.addEventListener) reduce.addEventListener('change', start);
    if (connection && connection.addEventListener) connection.addEventListener('change', start);
    window.addEventListener('pagehide', reset);
    window.addEventListener('pageshow', function (event) { if (event.persisted) start(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
