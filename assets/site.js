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
