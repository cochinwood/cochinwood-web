/* Wood hub enhancement. Native categories and the full A-Z list need no script. */
(function () {
  'use strict';
  var controls = document.querySelector('[data-wood-controls]');
  if (!controls) return;
  var cards = Array.from(document.querySelectorAll('[data-wood-card]'));
  var groups = Array.from(document.querySelectorAll('[data-wood-group]'));
  var filters = Array.from(controls.querySelectorAll('[data-wood-filter]'));
  var input = document.getElementById('cw-wood-search');
  var clear = document.getElementById('cw-wood-clear');
  var count = document.getElementById('cw-wood-count');
  var empty = document.getElementById('cw-wood-empty');
  var selected = 'all';
  if (!input || !cards.length) return;
  function apply(updateUrl) {
    var query = input.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (card) {
      var match = (selected === 'all' || card.dataset.woodCard === selected) &&
        (!query || card.dataset.woodSearch.toLowerCase().indexOf(query) !== -1);
      card.hidden = !match;
      if (match) shown++;
    });
    groups.forEach(function (group) {
      group.hidden = !cards.some(function (card) { return !card.hidden && card.dataset.woodCard === group.dataset.woodGroup; });
    });
    filters.forEach(function (filter) {
      if (filter.dataset.woodFilter === selected) filter.setAttribute('aria-current', 'true');
      else filter.removeAttribute('aria-current');
    });
    count.textContent = shown + (shown === 1 ? ' species matches' : ' species match') + (query ? ' your search' : ' these categories');
    clear.hidden = !query && selected === 'all';
    empty.hidden = shown !== 0;
    if (updateUrl) {
      var params = new URLSearchParams(location.search);
      if (query) params.set('q', input.value.trim()); else params.delete('q');
      if (selected !== 'all') params.set('group', selected); else params.delete('group');
      var search = params.toString();
      history.replaceState(null, '', location.pathname + (search ? '?' + search : '') + '#wood-browse');
    }
  }
  function restore() {
    var params = new URLSearchParams(location.search);
    var requested = params.get('group');
    selected = filters.some(function (filter) { return filter.dataset.woodFilter === requested; }) ? requested : 'all';
    input.value = params.get('q') || '';
    apply(false);
  }
  input.addEventListener('input', function () { apply(true); });
  input.addEventListener('search', function () { apply(true); });
  clear.addEventListener('click', function () { input.value = ''; selected = 'all'; apply(true); input.focus(); });
  filters.forEach(function (filter) {
    filter.addEventListener('click', function (event) {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      selected = filter.dataset.woodFilter;
      apply(true);
      controls.scrollIntoView({ behavior: 'auto', block: 'start' });
    });
  });
  window.addEventListener('popstate', restore);
  restore();
})();
