# Branch map — read this before changing anything

## You are on `cf-live`. This is production.

Cloudflare Pages serves this branch **verbatim** at https://www.cochinwood.in.
What is committed here is exactly what a visitor receives. There is no build step,
no generator, no package manager, no `dist/`. You edit the `.html` files directly.

Verified 2026-08-15: the live homepage is byte-identical to `index.html` on this
branch, apart from Cloudflare's own edge injection — it rewrites `mailto:` links
into `/cdn-cgi/l/email-protection` and adds `email-decode.min.js`. That difference
is Cloudflare's, not ours, and must never be "fixed".

Re-verify at any time:

    git show origin/cf-live:index.html > /tmp/repo.html
    curl -s https://www.cochinwood.in/ > /tmp/live.html
    diff /tmp/repo.html /tmp/live.html

## The Zoho strings are fossils, not a live Zoho site

This branch descends from a static mirror of CWI's former Zoho Sites site, so the
HTML still contains `zsite-core.css`, `zs-customcss.css`, a `zs_rendering_mode`
global, and `/template/55562362302e4b8a8860fffaee39d549/...`. `/css/zsite-core.css`
returns HTTP 200.

**CWI is fully off Zoho Sites.** Every one of those files is committed in this repo
and served by Cloudflare. Nothing calls out to Zoho. Reading "zsite" in the markup
and concluding the site still runs on Zoho is a mistake that has already been made
once — check `git ls-tree -r origin/cf-live` to see where a file comes from, rather
than inferring the host from the markup's vocabulary.

Some of that inheritance is dead weight worth removing for load speed. Some of it
the mirrored layout still depends on. Never delete Zoho-era CSS, JS or markup
without first proving in a browser that the affected pages render identically
before and after, at both 375px and 1280px.

## Branches

| Branch | What it is | Deployed |
|---|---|---|
| `cf-live` | The live site. ~293 hand-maintained `.html` files, no build step. | **yes — production** |
| `master` | A clean Python SSG rebuild (`build.py` → `dist/`) intended to replace this branch. See `CUTOVER-PLAN.md` there. | no |

Work landed on `master` reaches no users today.

## `cf-live` is gated, because on this branch a push IS a deploy

Pages publishes the moment `cf-live` moves, so a check that ran afterwards was
telling you about pages buyers were already reading. Since 15 Aug 2026 the branch
requires the **`The site says one thing`** status check to pass before a commit can
land: work on another branch, let the check run there, then merge or fast-forward.

The check is `.github/workflows/site-checks.yml` here, running `tools/check_site.py`
from `master` — it is not in this branch because Pages would publish it. It verifies
that every `ld+json` block parses, that the continent count in the copy matches the
country list, that no two `_headers` rules setting `Cache-Control` can match one path,
that every root-relative link is a committed file or a `_redirects` rule, and that the
quote form still posts to `/web-lead` with its honeypot and Turnstile error-callback.

Administrators can still bypass — deliberately, so a broken checker or a GitHub outage
cannot stop you rolling back. That escape hatch is for emergencies, not for skipping a
red check.

## Merging deploys the origin and purges nothing

A merge into `cf-live` republishes the origin. It does **not** clear Cloudflare's
edge cache, so a page already cached keeps being served until its TTL runs out —
the same URL can return the old document to a visitor and the new one to anyone
who adds a query string.

Measured on 28 Aug 2026, about two hours after a merge:

    https://www.cochinwood.in/            cf-cache-status: HIT   Age: 7148   (pre-merge copy)
    https://www.cochinwood.in/?cb=<rand>  cf-cache-status: MISS              (correct)

That instance cost the `/cw-event` counter its most-visited page: the homepage was
serving a document without `js/cw-events.js`, so the dashboard would have reported
the homepage producing no quote clicks — a wrong answer rather than a missing one.

**The app repo does not have this problem, which is why it is easy to forget here.**
`webapp/deploy.py` purges the edge for `app.cochinwood.in` on every shell deploy and
says so in its output. There is no equivalent step on this side, because there is no
deploy script on this side at all — the merge is the deploy.

So after merging anything whose correctness is time-sensitive — a price, a phone
number, a contact CTA, a legal line — purge the affected URLs and then re-fetch them
WITHOUT a cache-buster to confirm. A cache-buster proves the origin is right and
proves nothing about what a visitor receives.

    POST https://api.cloudflare.com/client/v4/zones/<zone>/purge_cache
    {"files": ["https://www.cochinwood.in/", "https://cochinwood.in/"]}

Purge the specific URLs rather than the zone: a full purge sends every page to the
origin at once for no benefit when two files changed.

ONE READING TRAP, PAID FOR ONCE. `/index.html` answers `BYPASS` with an empty body —
that is a 308 to `/`, not a document, and reading it as "reached the origin and the
origin is wrong" turns a cache problem into an imaginary build problem. Probe the URL
a visitor actually requests.

## The 292 email-decode tags look dead and are not safe to delete

Every page carries

    <script data-cfasync="false" src="/cdn-cgi/scripts/.../email-decode.min.js"></script>

and since the 28 Aug sweep there is **not a single `__cf_email__` left in the source** — so the
decoder has nothing in this repo to decode, and reads as obvious dead weight. Delete it on that
reasoning and you may break every email link on the site.

**Whether it is dead depends on a switch that is not in this repo.** Scrape Shield → Email
Obfuscation, on the Cloudflare zone, rewrites plain `mailto:` links into `__cf_email__` placeholders
*at the edge, on the way out*. While it is on, the served page needs a decoder and the repo looks
like it has none — and while it is off, the repo looks like it has a decoder for nothing. The
source is the same either way. Nothing you can grep for tells you which state you are in.

Measured 28 Aug 2026, after the setting was turned **off**:

    live /contact   __cf_email__ 0   email-decode.min.js 2
    source          __cf_email__ 0   email-decode.min.js 2

Live and source agree, which is how we know these tags are **ours** — committed into the HTML,
almost certainly fossilised from a Cloudflare pass years ago the same way the Zoho strings were —
rather than injected fresh on each request.

**So before removing them**, check the setting rather than the markup:

    GET https://api.cloudflare.com/client/v4/zones/<zone>/settings/email_obfuscation

If it reads `off`, they are genuinely inert and removable. If it reads `on`, they may be the only
thing decoding the addresses on 292 pages, and *that* has not been tested — nobody has established
whether Cloudflare would inject its own decoder in their absence.

**Why the setting is off.** With it on, a no-JS crawler receives `[email protected]` instead of an
address — including on `llms.html`, which exists specifically for JS-less AI clients. The trade
accepted on 28 Aug is that plain `mailto:` links are scrapeable by spam bots. If the spam becomes a
problem, turning it back on is one PATCH to the endpoint above — and at that moment these tags stop
being dead weight again.

## Config files

- `_headers`, `_redirects` — Cloudflare Pages config, hand-maintained.
- `_redirects` is first-match-wins, and Pages drops `:splat` in some rule forms.
  Both have caused regressions in this repo before.
- `robots.txt`, `sitemap.xml` — hand-maintained; keep them in step with the pages
  that actually exist.

## Caching

Fixed 2026-08-15. Only `assets/fonts/*.woff2` carry a hash in the filename, so
only they are served `immutable` for a year. Everything else with a stable
filename — `assets/fonts.css`, `css/zsite-core.css`, `js/zsite-core.js`, the
`template/` stylesheets — is `max-age=3600, must-revalidate`, because an edit to
those does not change their URL and `immutable` would hide the change from
returning visitors for up to a year.

Note when editing `_headers`: Cloudflare Pages **merges every matching rule**
rather than letting the most specific one win. Two rules matching one path append
two `Cache-Control` values into a single header. Keep the path patterns disjoint —
this is why `/assets/fonts.css` and `/assets/og/*` are named individually instead
of using `/assets/*`.

## The Zoho theme CSS is purged — regenerate it, don't hand-edit

`css/zsite-core.css` and `template/<id>/stylesheets/*.css` are Zoho theme
stylesheets carried over by the mirror. Well over 90% of their rules could never
match any element on this site, so on 2026-08-15 they were reduced with the purge
script: 264KB + 188KB + 1.3KB of CSS became 40KB + 42KB + 124B.

The script lives on the **`master`** branch at `tools/purge-css.py`, deliberately
not here — Cloudflare Pages publishes every committed file on this branch, and
`master` is not deployed. Fetch it without switching branches:

    git show master:tools/purge-css.py > /tmp/purge-css.py

The script keeps a selector when every class and id token in it appears somewhere
in the 293 HTML files **or** in any JavaScript string literal (so runtime-added
class names survive), and keeps tag-only, attribute and `:root` selectors
unconditionally.

**If you add markup that uses a Zoho theme class not currently on the site, its
styling will be missing.** Restore the full stylesheet from git history, add the
markup, then re-run:

    python /tmp/purge-css.py css/zsite-core.css \
      template/<id>/stylesheets/style.css template/<id>/stylesheets/sub-style.css

Verify the same way it was verified originally: serve the before and after trees
on two ports, and for each page compare a digest of `getComputedStyle` across
every element in `body`. **Wait for `document.fonts.ready` plus a settle delay
before measuring** — measuring during webfont load produces false differences,
which cost an hour the first time.

## Automated audit

A scheduled cloud routine audits this branch every 6 hours and opens a single
`audit/<date>` PR against `cf-live`. It must verify every finding against the
actual file before fixing, and opens no PR when nothing survives verification.

## Export reach: FIVE continents, and the fifth is Chile

**Do not "correct" this to four.** The `cochin-wood-brand-voice` skill may still
say *"four continents, not five — never write five continents."* That card is
STALE. Edwin confirmed Chile as a live South American market on 15 Aug 2026 and
the site was updated in `810e7b5b`. This file is the authority; the skill loses.

| Continent | Markets |
|---|---|
| Asia | India (domestic), Sri Lanka, Turkey, GCC — UAE, Saudi Arabia, Qatar, Oman, Kuwait, Bahrain |
| Africa | South Africa, Nigeria, Kenya |
| Europe | Netherlands |
| North America | United States, Haiti, Puerto Rico, Dominican Republic |
| South America | **Chile** |

**Never move the number without the list.** 292 pages carry a JSON-LD FAQ
answering *"Which export markets do you currently ship to?"* with the countries
spelled out. Changing the headline count alone leaves the site claiming one
number in the copy Google reads and another in the data Google indexes — worse
than either version, and the exact self-refuting shape the 10 Aug 2026 audit
existed to remove. Re-parse every `ld+json` block after such an edit; there were
1431 of them and all were checked that day.

**The fifth continent rests on Chile alone.** Haiti, Puerto Rico and the
Dominican Republic are Caribbean islands in **North** America. Reading them as
South America is what produced an earlier false five-continent claim, which is
why the count was cut to four in the first place. If Chile ever lapses, four
becomes correct again — so check the list, never repeat the number from memory.

Why this gets audited at all: an export-reach claim is among the easiest things
on the site for a buyer to check, so it has to match the country list exactly.

(Kept deliberately brief. This file is publicly readable — see the `/CLAUDE.md`
note in `_headers` — so commercial reasoning belongs in memory, not here.)
