"""Customer RFQ fields: one contact/destination, independently specified products."""
from html import escape, unescape

PRESETS = {
    'packing-plywood': 'Packing Plywood', 'commercial-plywood': 'Commercial Plywood',
    'okoume-plywood': 'Okoume Plywood', 'rubberwood-plywood': 'Rubberwood Plywood',
    'film-faced-shuttering-plywood': 'Film Faced/Shuttering',
    'marine-plywood': 'BWP Marine Plywood - IS 710',
    'bwr-hardwood-plywood': 'BWR Hardwood Plywood - IS 303',
    'container-flooring-plywood': 'Container Flooring',
    'block-board-flush-doors': 'Block Board/Flush Door',
    'plywood-boxes-crates': 'Wooden/Plywood Packing Case', 'plywood-pallets': 'Plywood Pallets',
    'sawn-timber': 'Timber/Runners/Planks', 'chequered-anti-skid-plywood': 'Chequered Anti-Skid Plywood',
    'finger-joint-board': 'Finger-Joint Board', 'particle-board': 'Particle Board',
    'plywood-cable-drums': 'Plywood Cable Drums',
    'premium-hardwood-plywood': 'Premium Hardwood Plywood',
}


def render_quote_form(products, incoterms, sitekey, script_src):
    options = []
    for value, label in products:
        if value == 'Commercial/Packing Grade':
            options.extend([('Commercial Plywood', 'Commercial plywood'), ('Packing Plywood', 'Packing plywood')])
        elif value == 'Wooden/Plywood Packing Case':
            options.extend([(value, 'Plywood boxes & crates'), ('Plywood Pallets', 'Plywood pallets')])
        else:
            options.append((value, unescape(label)))
    if not any(value == PRESETS['premium-hardwood-plywood'] for value, _label in options):
        options.append((PRESETS['premium-hardwood-plywood'], 'Premium Hardwood plywood'))
    choices = ''.join(f'<option value="{escape(v, quote=True)}">{escape(label)}</option>' for v, label in options)
    item = f'''<fieldset class="cw-quote-item" data-quote-item>
  <legend>Product <span data-item-number>1</span></legend>
  <div class="cw-quote-item__head"><p>Give this product its own specification and quantity.</p><button type="button" class="cw-quote-remove" data-remove-item hidden>Remove product</button></div>
  <div><label for="q-product-__INDEX__">Product type *</label><select id="q-product-__INDEX__" name="products" data-item-field="product" required><option value="">Choose a product</option>{choices}<option value="Help me choose">I need help choosing a product</option></select></div>
  <label class="cw-quote-help" for="q-help-__INDEX__"><input id="q-help-__INDEX__" name="help_me_choose" type="checkbox" value="1" data-item-field="help_me_choose">Help me choose this product or its specification</label>
  <div class="cw-row">
    <div><label for="q-grade-__INDEX__">Grade, if known</label><input id="q-grade-__INDEX__" name="grade" data-item-field="grade" maxlength="80" placeholder="e.g. BWP, IS 710" data-pack="Grade"></div>
    <div><label for="q-thickness-__INDEX__">Thickness, if known</label><input id="q-thickness-__INDEX__" name="thickness" data-item-field="thickness" maxlength="40" placeholder="e.g. 18 mm" data-pack="Thickness"></div>
  </div>
  <div class="cw-row">
    <div><label for="q-dimensions-__INDEX__">Size / dimensions, if known</label><input id="q-dimensions-__INDEX__" name="dimensions" data-item-field="dimensions" maxlength="80" placeholder="e.g. 2440 × 1220 mm" data-pack="Dimensions"></div>
    <div><label for="q-quantity-__INDEX__">Quantity, if known</label><input id="q-quantity-__INDEX__" name="quantity" data-item-field="quantity" maxlength="40" inputmode="decimal" placeholder="e.g. 500" data-pack="Quantity"></div>
  </div>
  <div><label for="q-unit-__INDEX__">Quantity unit</label><select id="q-unit-__INDEX__" name="unit" data-item-field="unit" data-pack="Unit"><option value="">Not sure yet</option><option>Sheets</option><option>Pieces</option><option>CBM</option><option>20ft containers</option><option>40ft containers</option></select></div>
</fieldset>'''
    basis = ''.join(f'<option>{escape(value)}</option>' for value in incoterms)
    # Only the first item exists without scripting and keeps the established native
    # field names. The additional template is inert until the buyer adds a product.
    return f'''<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer onerror="window.cwq2TsDead=1;window.cwq2TsNoload&amp;&amp;window.cwq2TsNoload()"></script>
<form class="cw-form cw-quote-form" id="cwq2-form" method="POST" action="https://www.cochinwood.in/web-lead" accept-charset="UTF-8" data-max-items="20">
  <input type="hidden" name="enquiry" value=""><input type="hidden" name="enquiry_id" value=""><input type="hidden" name="spec_grade" value="">
  <div class="cw-hp" aria-hidden="true"><label for="q-web">Leave this field empty</label><input id="q-web" name="cwq2_website" tabindex="-1" autocomplete="off"></div>
  <p class="cw-note" style="margin:0">Fields marked * are required. Add each product or size as a separate item.</p>
  <div class="cw-row"><div><label for="q-name">Name *</label><input id="q-name" name="name" autocomplete="name" maxlength="120" required></div><div><label for="q-co">Company *</label><input id="q-co" name="company" autocomplete="organization" maxlength="160" required></div></div>
  <div class="cw-row"><div><label for="q-em">Work email *</label><input id="q-em" type="email" name="email" autocomplete="email" maxlength="160" required></div><div><label for="q-ph">WhatsApp / phone *</label><input id="q-ph" type="tel" name="phone" autocomplete="tel" maxlength="40" required></div></div>
  <div id="cwq-items">{item.replace('__INDEX__', '1')}</div>
  <template id="cwq-item-template">{item}</template>
  <div class="cw-quote-add"><button type="button" class="cw-btn cw-btn--g" id="cwq-add-item" hidden>Add another product</button><p class="cw-note" id="cwq-item-status" role="status" aria-live="polite"></p></div>
  <p class="cw-note" id="q-guidance">Not sure of a specification? Choose “Help me choose” for that item and describe its use below.</p>
  <div class="cw-row"><div><label for="q-port">Delivery city / destination port *</label><input id="q-port" name="destination" maxlength="120" placeholder="e.g. Kochi, or Jebel Ali, UAE" required></div><div><label for="q-inco">Quote basis</label><select id="q-inco" name="incoterm" data-pack="Quote basis"><option value="">Not sure — advise me</option>{basis}</select></div></div>
  <div><label for="q-msg">Application / requirements</label><textarea id="q-msg" name="description" maxlength="4000" aria-describedby="q-guidance" placeholder="Tell us how you will use the products, delivery timing and any other requirements. Refer to product 1, product 2, and so on where helpful."></textarea></div>
  <div class="cf-turnstile" data-sitekey="{escape(sitekey, quote=True)}" data-size="flexible" data-theme="light" data-error-callback="cwq2TsFail" style="margin:0 0 14px"></div>
  <p class="cw-form__err" id="cwq2-error" role="alert"></p>
  <div><button class="cw-btn cw-btn--p" type="submit">Send enquiry</button><p class="cw-note" style="margin:10px 0 0">Goes straight to our sales desk. We reply within one business day.</p></div>
</form><script src="{escape(script_src, quote=True)}" defer></script>'''
