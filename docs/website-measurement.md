# Website measurement

The public website uses the existing company Google Tag Manager container
`GTM-K2DJRFM8` and GA4 stream `G-QD4G3EYG2G` (property `491827563`, web stream
`11307314845`). The stream name is **Cochin Wood — cochinwood.in** and its URL is
`https://www.cochinwood.in`. Enhanced measurement is disabled; events are explicit.

`assets/search-measurement.js` loads Google only on the production website after
an explicit, current analytics opt-in. The saved choice expires after 180 days.
The footer's Analytics choices control lets visitors change it. Denial does not
interfere with enquiries, and withdrawal disables further events and clears
accessible Google Analytics cookies. Local and hosted previews never load Google.

The implementation sends canonical paths without query strings or fragments,
origin-only referrers, public page titles and approved event names. It does not
send form values, customer contact information or search terms. Advertising
storage, advertising user data, personalization and Google Signals remain denied
or disabled. Google requests are absent before consent, rather than merely sent
with a denied state.

## Google Tag Manager version 3

Published on 6 September 2026 at 15:19 IST by the existing administrator. Version 2
remains available for rollback. Four changes were reviewed:

- New Google tag for the existing GA4 stream, with `send_page_view=false` and
  additional `analytics_storage` consent required.
- New custom-event trigger, `cwi_analytics_ready`, emitted after opting in and
  before the manual page-view event.
- Existing Page Visitors advertising tag now requires `ad_storage` and
  `ad_user_data`. Its existing destination and trigger were retained.
- Existing Conversion Linker now requires `ad_storage`; its settings were retained.

The site sends one `page_view` per opted-in page, product `view_item` events, quote
clicks, quote starts/validation errors and phone/WhatsApp interaction events.
Contact form views are deduplicated. A `?sent=1` URL is never treated as proof of
an accepted enquiry. Accepted-enquiry counts remain the independent server-side
first-party counters recorded only after the submission is accepted.

## Verification

`tools/test_search_measurement.cjs` covers consent, production/preview scoping,
sanitization, ordering, deduplication, withdrawal and keyboard/mobile controls.
A separate release check executed the actual published Google container against
the candidate site, intercepting collection to avoid polluting reports. It
observed exactly one correctly addressed `page_view` and one `view_item`, analytics
consent granted with advertising denied, no private URL data, no advertising
requests and no runtime errors. Production collection is verified separately
after the site is published; an intercepted request proves payload behavior,
not receipt in Analytics reporting.

Google tags measure activity; installing them does not directly increase organic
search rankings. Search Console, image sitemaps and IndexNow have distinct roles.
