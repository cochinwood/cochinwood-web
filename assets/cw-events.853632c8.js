/* Which page actually produces an enquiry.  (audit 2026-08-25, C-17)
 *
 * This site publishes 109 city guides and nothing counted whether one of them ever produced an
 * enquiry. Cloudflare Insights gives page views, cookieless, and supports no custom events — so
 * "which of these pages earns its keep", the question behind half the SEO findings in that audit,
 * had no answer.
 *
 * WHAT IS SENT, in full: an event name from a list of four, and the path of the page it happened
 * on. Nothing else. No cookie is set, no identifier is generated, no address is recorded at the
 * other end, and the counter it lands in is keyed only by (day, event, page). Two events cannot be
 * linked back to one person because nothing here says who anybody is — which is what keeps this
 * out of consent-banner territory, and it is a promise a test in the app repository enforces.
 *
 * THE ONE THING KEPT BETWEEN PAGES, and why it is still not tracking. A buyer reads a city guide,
 * taps "Request a quote", and submits the form on /contact. Keyed naively, every submission is
 * credited to /contact and the question "which guide produced it" stays unanswered — the whole
 * point, missed. So the guide's path is put in sessionStorage when they set off, and reported as
 * the origin when they arrive. That is one path, no identifier, per tab, gone when the tab closes,
 * never read by anything but this file, and the value that comes back is the same page key that
 * would have been sent anyway. It buys the actual answer for no new information about anybody.
 *
 * IT MUST NEVER BREAK THE PAGE IT IS WATCHING. Every listener is passive, every path is wrapped,
 * nothing calls preventDefault, and a browser without sendBeacon simply falls back. If this file
 * fails to load at all, every link on the site still works exactly as it did.
 *
 * COUNTED CLICKS ARE NOT PEOPLE. One person tapping WhatsApp twice is two. These are counters for
 * deciding where to spend writing effort, and comparing pages against each other is what they are
 * for; reading a single number as "enquiries" is not.
 */
(function () {
  "use strict";

  var ENDPOINT = "/cw-event";
  var ORIGIN_KEY = "cwq_from";           // sessionStorage: the page the buyer set off from

  function page() {
    try { return location.pathname || "/"; } catch (e) { return "/"; }
  }

  /* Live, the contact page is served at /contact and /contact.html 308s to it. Served directly —
     locally, or from any preview that hands back files — the extension is still there. They are the
     same page, and code that disagrees about that fails in the direction that looks fine: the
     suppression below stops working, so the contact page's own buttons get counted as enquiries
     coming from the contact page, and it tops every report it appears in. Found exactly that way,
     27 Aug 2026, on a local copy. */
  function isContact(p) { return /^\/contact(\.html)?(\/|$)/.test(p); }

  function send(name, path) {
    try {
      var u = ENDPOINT + "?n=" + encodeURIComponent(name) + "&p=" + encodeURIComponent(path || page());
      if (navigator.sendBeacon) navigator.sendBeacon(u);
      else fetch(u, { method: "POST", mode: "no-cors", keepalive: true });
    } catch (e) { /* a counter may never become something the buyer can see */ }
  }

  /* Delegated and captured, because the header, the footer and the mega-menu are all built by
     JavaScript after this runs — a listener bound to the links themselves would miss every one of
     them, and rebinding on mutation is how you end up counting the same click five times. */
  function anchorFrom(node) {
    try {
      for (var el = node; el && el !== document; el = el.parentNode) {
        if (el.tagName === "A" && el.getAttribute("href")) return el;
      }
    } catch (e) {}
    return null;
  }

  function classify(href, a) {
    if (/^tel:/i.test(href)) return "tel_click";
    if (/(^https?:)?\/\/(wa\.me|api\.whatsapp\.com)\//i.test(href) || /^whatsapp:/i.test(href)) {
      return "whatsapp_click";
    }
    /* A quote click is the intent to enquire: the header call-to-action, or any link into the
       contact page. Deliberately not counted when the buyer is ALREADY on /contact — a link from
       the contact page to the contact page says nothing about which page produced the intent, and
       counting it would put the site's own busiest button at the top of every report. */
    var onContact = isContact(page());
    if (!onContact) {
      if (a && a.className && String(a.className).indexOf("cw-hd-cta") >= 0) return "quote_click";
      if (/^\/contact(\.html)?(\/|#|\?|$)/.test(href)) return "quote_click";
      if (/^https?:\/\/(www\.)?cochinwood\.in\/contact(\.html)?(\/|#|\?|$)/i.test(href)) return "quote_click";
    }
    return null;
  }

  document.addEventListener("click", function (ev) {
    try {
      var a = anchorFrom(ev.target);
      if (!a) return;
      var name = classify(a.getAttribute("href") || "", a);
      if (!name) return;
      var from = page();
      if (name === "quote_click") {
        /* Remembered here rather than on arrival, because by the time they reach /contact the page
           they came from is gone. Wrapped: Safari in private mode throws on write. */
        try { sessionStorage.setItem(ORIGIN_KEY, from); } catch (e) {}
      }
      send(name, from);
    } catch (e) {}
  }, true);

  /* The form posts to a Worker which redirects back with ?sent=1, so a successful submission is a
     page load and not an event this file can hear. Read once, on load. */
  try {
    if (/[?&]sent=1(&|$)/.test(location.search) && isContact(page())) {
      var from = null;
      try { from = sessionStorage.getItem(ORIGIN_KEY); } catch (e) {}
      try { sessionStorage.removeItem(ORIGIN_KEY); } catch (e) {}
      /* Credited to the page the buyer set off from where that is known, and to /contact where they
         arrived directly — which is itself worth being able to tell apart. */
      send("form_submit_success", from || page());
    }
  } catch (e) {}
})();
