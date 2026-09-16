/* Cochin Wood Industries — site behaviour. No dependencies, no tracking. */
(function () {
  "use strict";

  /* ---- mobile navigation ------------------------------------------------ */
  var burger = document.querySelector(".cw-burger");
  var nav = document.getElementById("nav");

  if (burger && nav) {
    var setOpen = function (open) {
      nav.classList.toggle("open", open);
      burger.setAttribute("aria-expanded", open ? "true" : "false");
    };
    burger.addEventListener("click", function (e) {
      e.stopPropagation();
      setOpen(burger.getAttribute("aria-expanded") !== "true");
    });
    // close on Escape, on outside click, and after following a link
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && burger.getAttribute("aria-expanded") === "true") {
        setOpen(false);
        burger.focus();
      }
    });
    document.addEventListener("click", function (e) {
      if (burger.getAttribute("aria-expanded") !== "true") return;
      if (!nav.contains(e.target) && e.target !== burger) setOpen(false);
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) setOpen(false);
    });
  }

  /* ---- back to top ------------------------------------------------------ */
  var top = document.querySelector(".cw-top");
  if (top) {
    var onScroll = function () {
      var show = window.scrollY > 900;
      top.hidden = !show;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    top.addEventListener("click", function () {
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
      var skip = document.querySelector(".cw-skip");
      if (skip) skip.focus();
    });
  }

  /* ---- same-origin image preview --------------------------------------- */
  var imagePattern = /\.(?:avif|gif|jpe?g|png|svg|webp)$/i;
  var preview = null;
  var previewImage = null;
  var previewTitle = null;
  var previewOpener = null;
  var previewScrollY = 0;
  var previewScrollRestoration = null;
  var previewBackground = [];
  var previewClosing = false;

  // A reload cannot restore the original opener or its scroll position. Remove
  // a stale preview entry and return history scrolling to the browser default.
  if (history.state && history.state.cwImagePreview) {
    history.replaceState(null, "", location.href);
    if ("scrollRestoration" in history) history.scrollRestoration = "auto";
  }

  function imageLink(opener) {
    if (!opener) return null;
    var url;
    if (opener.matches("[data-image-preview]")) {
      try { url = new URL(opener.dataset.imagePreview, location.href); } catch (_error) { return null; }
      return url.origin === location.origin && imagePattern.test(url.pathname) && opener.querySelector("img") ? url : null;
    }
    if (opener.hasAttribute("download") || opener.matches('[rel~="license"]') || opener.closest(".cw-media-source")) return null;
    try { url = new URL(opener.href, location.href); } catch (_error) { return null; }
    if (url.origin !== location.origin || !imagePattern.test(url.pathname)) return null;
    return url;
  }

  function ensurePreview() {
    if (preview) return;
    preview = document.createElement("div");
    preview.className = "cw-image-preview";
    preview.hidden = true;
    preview.setAttribute("role", "dialog");
    preview.setAttribute("aria-modal", "true");
    preview.setAttribute("aria-labelledby", "cw-image-preview-title");
    preview.innerHTML = '<div class="cw-image-preview__bar">'
      + '<button type="button" class="cw-image-preview__back">← Back to page</button>'
      + '<strong id="cw-image-preview-title">Image preview</strong>'
      + '<button type="button" class="cw-image-preview__close" aria-label="Close image preview">Close</button>'
      + '</div><div class="cw-image-preview__stage"><img alt=""></div>';
    document.body.appendChild(preview);
    previewImage = preview.querySelector("img");
    previewTitle = preview.querySelector("strong");
    preview.querySelectorAll("button").forEach(function (button) {
      button.addEventListener("click", requestPreviewClose);
    });
    preview.addEventListener("click", function (event) {
      if (event.target === preview || event.target.classList.contains("cw-image-preview__stage")) requestPreviewClose();
    });
    preview.addEventListener("keydown", function (event) {
      if (event.key !== "Tab") return;
      var controls = Array.from(preview.querySelectorAll("button"));
      var first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
  }

  function showPreview(state, opener) {
    var alreadyOpen = preview && !preview.hidden;
    ensurePreview();
    previewOpener = opener || previewOpener;
    if (!alreadyOpen) {
      previewScrollY = window.scrollY;
      if ("scrollRestoration" in history && previewScrollRestoration === null) {
        previewScrollRestoration = history.scrollRestoration;
        history.scrollRestoration = "manual";
      }
    }
    previewImage.src = state.src;
    previewImage.alt = state.alt || "Image preview";
    previewTitle.textContent = state.alt || "Image preview";
    preview.hidden = false;
    if (!alreadyOpen) {
      previewBackground = Array.from(document.body.children).filter(function (element) { return element !== preview; }).map(function (element) {
        var state = { element: element, inert: element.inert, ariaHidden: element.getAttribute("aria-hidden") };
        element.inert = true;
        element.setAttribute("aria-hidden", "true");
        return state;
      });
    }
    document.body.classList.add("cw-image-preview-open");
    if (!alreadyOpen) preview.querySelector(".cw-image-preview__back").focus();
  }

  function hidePreview() {
    previewClosing = false;
    if (!preview || preview.hidden) return;
    preview.hidden = true;
    previewImage.removeAttribute("src");
    document.body.classList.remove("cw-image-preview-open");
    previewBackground.forEach(function (state) {
      state.element.inert = state.inert;
      if (state.ariaHidden === null) state.element.removeAttribute("aria-hidden");
      else state.element.setAttribute("aria-hidden", state.ariaHidden);
    });
    previewBackground = [];
    if (previewOpener && previewOpener.isConnected) previewOpener.focus({ preventScroll: true });
    window.scrollTo(0, previewScrollY);
    requestAnimationFrame(function () {
      window.scrollTo(0, previewScrollY);
      if (previewScrollRestoration !== null) {
        history.scrollRestoration = previewScrollRestoration;
        previewScrollRestoration = null;
      }
    });
  }

  function requestPreviewClose() {
    if (previewClosing || !preview || preview.hidden) return;
    if (history.state && history.state.cwImagePreview) {
      previewClosing = true;
      history.back();
    }
    else hidePreview();
  }

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || !preview || preview.hidden) return;
    event.preventDefault();
    event.stopPropagation();
    requestPreviewClose();
  }, true);

  document.addEventListener("click", function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var opener = event.target.closest("[data-image-preview],a[href]");
    var url = imageLink(opener);
    if (!url) return;
    event.preventDefault();
    var image = opener.querySelector("img");
    var label = image && image.alt || opener.getAttribute("aria-label") || opener.textContent || url.pathname.split("/").pop();
    var state = { cwImagePreview: true, src: url.href, alt: label.trim() };
    history.pushState(state, "", location.href);
    showPreview(state, opener);
  });

  window.addEventListener("popstate", function (event) {
    previewClosing = false;
    if (event.state && event.state.cwImagePreview) showPreview(event.state, null);
    else hidePreview();
  });

  /* ---- blog topics and search ------------------------------------------ */
  var box = document.getElementById("cw-blogsearch");
  if (box) {
    var cards = Array.from(document.querySelectorAll(".cw-bloglist > a"));
    var groups = Array.from(document.querySelectorAll("[data-blog-group]"));
    var topics = Array.from(document.querySelectorAll("[data-blog-topic-filter]"));
    var count = document.getElementById("cw-blogcount");
    var empty = document.getElementById("cw-blogempty");
    var clear = document.getElementById("cw-blogclear");
    var selected = "all";
    cards.forEach(function (card) { card.dataset.hay = (card.textContent || "").toLowerCase(); });
    function apply(updateUrl) {
      var q = box.value.trim().toLowerCase(), shown = 0;
      cards.forEach(function (card) {
        var hit = (selected === "all" || card.dataset.blogTopic === selected) && (!q || card.dataset.hay.indexOf(q) !== -1);
        card.hidden = !hit; if (hit) shown++;
      });
      groups.forEach(function (group) {
        var hits = Array.from(group.querySelectorAll(".cw-bloglist > a")).filter(function (c) { return !c.hidden; }).length;
        group.hidden = !hits;
        var label = group.querySelector(".cw-blog-group-count");
        if (label) label.textContent = hits + (hits === 1 ? " guide" : " guides");
      });
      topics.forEach(function (topic) {
        if (topic.dataset.blogTopicFilter === selected) topic.setAttribute("aria-current", "true");
        else topic.removeAttribute("aria-current");
      });
      if (count) count.textContent = shown + (shown === 1 ? " guide" : " guides") + (q ? ' matching “' + box.value.trim() + '”' : " available") + (selected === "all" ? " across all topics" : " in this topic");
      if (empty) empty.hidden = shown !== 0;
      if (clear) clear.hidden = !q && selected === "all";
      if (updateUrl && window.history && history.replaceState) {
        var params = new URLSearchParams(location.search);
        if (q) params.set("q", box.value.trim()); else params.delete("q");
        if (selected !== "all") params.set("topic", selected); else params.delete("topic");
        var query = params.toString();
        history.replaceState(null, "", location.pathname + (query ? "?" + query : "") + "#articles");
      }
    }
    function restore() {
      var params = new URLSearchParams(location.search), requested = params.get("topic");
      selected = topics.some(function (t) { return t.dataset.blogTopicFilter === requested; }) ? requested : "all";
      box.value = params.get("q") || ""; apply(false);
    }
    box.addEventListener("input", function () { apply(true); });
    box.addEventListener("search", function () { apply(true); });
    topics.forEach(function (topic) {
      topic.addEventListener("click", function (event) {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault(); selected = topic.dataset.blogTopicFilter; apply(true);
        var start = document.getElementById("articles");
        if (start) start.scrollIntoView({behavior: "auto", block: "start"});
      });
    });
    if (clear) clear.addEventListener("click", function () { box.value = ""; selected = "all"; apply(true); box.focus(); });
    window.addEventListener("popstate", restore);
    restore();
  }

  /* A buyer can take the comparison to a purchasing meeting or a factory call.
     Keep this in the shared script so the button works under the site's CSP and
     the print view remains a normal browser action with no extra page or route. */
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-print-catalogue]");
    if (!button) return;
    event.preventDefault();
    window.print();
  });

  /* ---- Quick Search / Spec Quick Finder --------------------------------- */
  var searchIndex = [
    { title: "Request Factory Quote", desc: "Online quote form with direct sales line & WhatsApp", url: "/contact#quote", cat: "Tool" },
    { title: "Direct Sales Team Directory", desc: "Direct phone, WhatsApp & language preferences for sales managers", url: "/contact#cw-sales-section", cat: "Tool" },
    { title: "Container Sheet & Weight Calculator", desc: "20ft & 40ft container capacity & weight limits calculator", url: "/rubberwood-plywood-container-weight", cat: "Tool" },
    { title: "Perumbavoor Plywood Price Tracker", desc: "Regional market price trends, raw material indices & timber rates", url: "/perumbavoor-plywood-price-tracker", cat: "Tool" },
    { title: "Full Product Catalogue", desc: "Complete range with category filtering & specifications", url: "/products", cat: "Product" },
    { title: "Packing Plywood", desc: "Custom thickness, packaging grade, Perumbavoor direct", url: "/packing-plywood", cat: "Product" },
    { title: "Marine Plywood (IS 710)", desc: "Boiling waterproof (BWP) grade, 72h boiling test certified", url: "/marine-plywood", cat: "Product" },
    { title: "Okoume Plywood", desc: "Gabon Okoume face, furniture, yachting, exterior grade", url: "/okoume-plywood", cat: "Product" },
    { title: "Rubberwood Plywood", desc: "Sustainable plantation hardwood, kiln-seasoned core", url: "/rubberwood-plywood", cat: "Product" },
    { title: "Commercial Plywood (IS 303 MR)", desc: "Moisture resistant interior grade for furniture & panelling", url: "/commercial-plywood", cat: "Product" },
    { title: "Film-Faced Shuttering Plywood", desc: "12mm & 18mm, 30+ repetitions, construction formwork", url: "/film-faced-shuttering-plywood", cat: "Product" },
    { title: "BWR Hardwood Plywood", desc: "Boiling water resistant, phenol formaldehyde bonded", url: "/bwr-hardwood-plywood", cat: "Product" },
    { title: "Chequered Anti-Skid Plywood", desc: "High-friction wiremesh flooring for trucks, containers & ramps", url: "/chequered-anti-skid-plywood", cat: "Product" },
    { title: "Container Flooring Plywood", desc: "28mm 19-ply, IICL compliant, heavy cargo repair panels", url: "/container-flooring-plywood", cat: "Product" },
    { title: "Plywood Boxes & Crates", desc: "ISPM-15 heat-treated export packaging & heavy machinery crates", url: "/plywood-boxes-crates", cat: "Product" },
    { title: "Plywood Pallets", desc: "Two-way and four-way export logistics pallets", url: "/plywood-pallets", cat: "Product" },
    { title: "Cable Drums", desc: "Wooden cable drums, reels & flanges", url: "/plywood-cable-drums", cat: "Product" },
    { title: "Sawn Timber", desc: "Kiln-dried sawn timber, runners & battens", url: "/sawn-timber", cat: "Product" },
    { title: "Finger Joint Board", desc: "Kiln-seasoned plantation hardwood solid boards", url: "/finger-joint-board", cat: "Product" },
    { title: "Block Board & Flush Doors", desc: "Solid core block boards and commercial flush doors", url: "/block-board-flush-doors", cat: "Product" },
    { title: "Wood Encyclopedia", desc: "28 commercial & native timber species reference", url: "/woods-we-use", cat: "Species" },
    { title: "Rubberwood (Hevea brasiliensis)", desc: "Density ~595 kg/m³, plantation timber, core & furniture", url: "/woods-we-use/rubberwood", cat: "Species" },
    { title: "Gurjan / Keruing (Dipterocarpus spp.)", desc: "Density ~750 kg/m³, premium marine face veneer", url: "/woods-we-use/gurjan", cat: "Species" },
    { title: "Okoume (Aucoumea klaineana)", desc: "Density ~430 kg/m³, lightweight marine & exterior face", url: "/woods-we-use/okoume", cat: "Species" },
    { title: "Teak (Tectona grandis)", desc: "Density ~650 kg/m³, luxury interior & exterior timber", url: "/woods-we-use/teak", cat: "Species" },
    { title: "Eucalyptus (Eucalyptus spp.)", desc: "Hardwood core veneer for structural plywood", url: "/woods-we-use/eucalyptus", cat: "Species" },
    { title: "Birch (Betula spp.)", desc: "High-density multi-ply architectural grade", url: "/woods-we-use/birch", cat: "Species" },
    { title: "Export Hub & Global Supply", desc: "Ports, shipping terms (FOB/CIF), documents & 27 country guides", url: "/export", cat: "Tool" },
    { title: "Company Verification & Credentials", desc: "Govt Verified IEC AAJCC9689H, FIEO RCMC, GST, CIN", url: "/company-verification", cat: "Tool" },
    { title: "Industries We Serve", desc: "Packaging, construction, marine, logistics, automotive & furniture", url: "/industries", cat: "Tool" },
    { title: "Frequently Asked Questions (FAQ)", desc: "ISPM-15, minimum order quantities, delivery & payment terms", url: "/faq", cat: "Tool" }
  ];

  function setupQuickSearch() {
    var headerIn = document.querySelector(".cw-hd__in");
    if (!headerIn || headerIn.querySelector(".cw-search-trigger")) return;

    var trigger = document.createElement("button");
    trigger.className = "cw-search-trigger";
    trigger.type = "button";
    trigger.setAttribute("aria-label", "Search products, timber species, certifications");
    trigger.title = "Search (Ctrl+K or /)";
    trigger.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>' +
      '<span class="cw-search-trigger__text">Search</span>' +
      '<kbd class="cw-search-trigger__kbd">Ctrl K</kbd>';

    var burger = headerIn.querySelector(".cw-burger");
    if (burger) {
      headerIn.insertBefore(trigger, burger);
    } else {
      headerIn.appendChild(trigger);
    }

    var modal = document.createElement("div");
    modal.className = "cw-search-modal";
    modal.hidden = true;
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-label", "Site Quick Search");
    modal.innerHTML = '<div class="cw-search-backdrop"></div>' +
      '<div class="cw-search-card">' +
        '<div class="cw-search-input-wrap">' +
          '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>' +
          '<input type="search" class="cw-search-input" placeholder="Search products, IS 710, rubberwood, container calc..." aria-label="Search site">' +
          '<button type="button" class="cw-search-close" aria-label="Close search">✕</button>' +
        '</div>' +
        '<div class="cw-search-results" role="listbox"></div>' +
        '<div class="cw-search-foot">' +
          '<span>Navigate <kbd>↑</kbd><kbd>↓</kbd></span>' +
          '<span>Select <kbd>↵</kbd></span>' +
          '<span>Close <kbd>esc</kbd></span>' +
        '</div>' +
      '</div>';
    document.body.appendChild(modal);

    var input = modal.querySelector(".cw-search-input");
    var resultsBox = modal.querySelector(".cw-search-results");
    var closeBtn = modal.querySelector(".cw-search-close");
    var backdrop = modal.querySelector(".cw-search-backdrop");
    var activeIdx = -1;

    function openModal() {
      modal.hidden = false;
      input.value = "";
      renderResults("");
      input.focus();
    }

    function closeModal() {
      modal.hidden = true;
      trigger.focus();
    }

    function renderResults(q) {
      var query = (q || "").trim().toLowerCase();
      var matches = searchIndex.filter(function (item) {
        if (!query) return true;
        return item.title.toLowerCase().indexOf(query) !== -1 ||
          item.desc.toLowerCase().indexOf(query) !== -1 ||
          item.cat.toLowerCase().indexOf(query) !== -1;
      }).slice(0, 8);

      activeIdx = matches.length ? 0 : -1;

      if (!matches.length) {
        resultsBox.innerHTML = '<div style="padding: 24px; text-align: center; color: #64748b; font-size: .88rem;">No matching products, species or tools found. Try searching "marine", "rubberwood", "quote" or "container".</div>';
        return;
      }

      resultsBox.innerHTML = matches.map(function (item, idx) {
        var badgeCls = item.cat === "Product" ? "cw-search-badge--product" : (item.cat === "Species" ? "cw-search-badge--species" : "cw-search-badge--tool");
        var activeCls = idx === 0 ? " active" : "";
        return '<a href="' + item.url + '" class="cw-search-item' + activeCls + '" data-idx="' + idx + '" role="option">' +
          '<div class="cw-search-item-info">' +
            '<span class="cw-search-item-title">' + item.title + '</span>' +
            '<span class="cw-search-item-desc">' + item.desc + '</span>' +
          '</div>' +
          '<span class="cw-search-badge ' + badgeCls + '">' + item.cat + '</span>' +
        '</a>';
      }).join("");
    }

    function updateActive(idx) {
      var items = resultsBox.querySelectorAll(".cw-search-item");
      if (!items.length) return;
      if (idx < 0) idx = items.length - 1;
      if (idx >= items.length) idx = 0;
      activeIdx = idx;
      items.forEach(function (el, i) {
        el.classList.toggle("active", i === activeIdx);
        if (i === activeIdx) el.scrollIntoView({ block: "nearest" });
      });
    }

    trigger.addEventListener("click", openModal);
    closeBtn.addEventListener("click", closeModal);
    backdrop.addEventListener("click", closeModal);

    input.addEventListener("input", function () {
      renderResults(input.value);
    });

    modal.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        closeModal();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        updateActive(activeIdx + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        updateActive(activeIdx - 1);
      } else if (e.key === "Enter") {
        var items = resultsBox.querySelectorAll(".cw-search-item");
        if (items.length && activeIdx >= 0 && items[activeIdx]) {
          e.preventDefault();
          window.location.href = items[activeIdx].getAttribute("href");
        }
      }
    });

    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        if (modal.hidden) openModal(); else closeModal();
      } else if (e.key === "/" && modal.hidden) {
        var tag = (document.activeElement && document.activeElement.tagName) || "";
        if (tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") {
          e.preventDefault();
          openModal();
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupQuickSearch);
  } else {
    setupQuickSearch();
  }
})();
