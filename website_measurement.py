"""Shared optional-analytics controls. No Google request before a saved opt-in."""
def controls(link):
    return f'''<button class="cw-privacy-settings" type="button" data-cwi-privacy-open aria-controls="cwi-privacy" aria-expanded="false" hidden>Analytics choices</button>
<section class="cw-privacy" id="cwi-privacy" role="region" aria-labelledby="cwi-privacy-title" hidden>
  <h2 id="cwi-privacy-title">Your privacy choices</h2>
  <p>With your permission, Google Analytics helps us understand which products and guides are useful. Your quote details are never sent to Google Analytics. The site works with essential services only. <a href="{link('/privacy-policy')}">Privacy policy</a></p>
  <div class="cw-privacy__actions"><button type="button" data-cwi-consent="denied">Essential only</button><button type="button" data-cwi-consent="accepted">Allow analytics</button></div>
</section>'''
