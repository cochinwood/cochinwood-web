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

  /* ---- blog filter ------------------------------------------------------ */
  var box = document.getElementById("cw-blogsearch");
  if (box) {
    var lists = Array.prototype.slice.call(document.querySelectorAll(".cw-bloglist"));
    var cards = Array.prototype.slice.call(document.querySelectorAll(".cw-bloglist > a"));
    var count = document.getElementById("cw-blogcount");
    var empty = document.getElementById("cw-blogempty");

    cards.forEach(function (c) {
      c.dataset.hay = (c.textContent || "").toLowerCase();
    });

    var apply = function () {
      var q = box.value.trim().toLowerCase();
      var shown = 0;
      cards.forEach(function (c) {
        var hit = !q || c.dataset.hay.indexOf(q) !== -1;
        c.hidden = !hit;
        if (hit) shown++;
      });
      // hide a group heading + list when everything inside it is filtered out,
      // and show the matched count rather than the stale total
      lists.forEach(function (l) {
        var hits = Array.prototype.filter.call(l.children, function (c) { return !c.hidden; }).length;
        l.hidden = !hits;
        var h = l.previousElementSibling;
        if (!h || h.tagName !== "H2") return;
        h.hidden = !hits;
        if (!h.dataset.label) h.dataset.label = h.textContent.replace(/\s*\(\d+\)\s*$/, "");
        h.textContent = h.dataset.label + " (" + (q ? hits : l.children.length) + ")";
      });
      if (count) {
        count.textContent = q
          ? shown + (shown === 1 ? " post matches " : " posts match ") + '"' + box.value.trim() + '"'
          : "";
      }
      if (empty) empty.hidden = shown !== 0;
    };

    box.addEventListener("input", apply);
    box.addEventListener("search", apply);
    // deep-link support: /blogs?q=marine
    var q0 = new URLSearchParams(location.search).get("q");
    if (q0) { box.value = q0; }
    apply();
  }
})();
