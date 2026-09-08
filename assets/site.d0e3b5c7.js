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
})();
