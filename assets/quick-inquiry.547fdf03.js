(function () {
  'use strict';
  var forms = document.querySelectorAll('[data-quick-inquiry]');
  if (!forms.length) return;
  forms.forEach(function (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var product = form.getAttribute('data-product') || 'plywood';
      var name = String(data.get('name') || '').trim();
      var phone = String(data.get('phone') || '').trim();
      var spec = String(data.get('spec') || '').trim();
      var quantity = String(data.get('quantity') || '').trim();
      var status = form.querySelector('[data-quick-status]');
      if (!name || !phone || !spec || !quantity) {
        if (status) status.textContent = 'Please complete all four fields so the desk can reply accurately.';
        return;
      }
      var message = [
        'Hello Cochin Wood, I would like a written quote.',
        'Product: ' + product,
        'Name: ' + name,
        'Phone or WhatsApp: ' + phone,
        'Thickness / sheet size: ' + spec,
        'Quantity or use: ' + quantity,
        'Please confirm price, availability, lead time and terms.'
      ].join('\n');
      var url = 'https://wa.me/919567410175?text=' + encodeURIComponent(message);
      var fallbackUrl = '/contact?product=' + encodeURIComponent(product.toLowerCase().replace(/\s+/g, '-')) + '#quote';
      if (status) {
        status.innerHTML = 'Connecting to WhatsApp… If WhatsApp did not open, <a href="' + url + '" target="_blank" rel="noopener" style="text-decoration:underline;font-weight:600">click here</a> or <a href="' + fallbackUrl + '" style="text-decoration:underline;font-weight:600">submit via web form</a>.';
      }
      var opened = window.open(url, '_blank', 'noopener,noreferrer');
      if (!opened) window.location.href = url;
    });
  });
}());
