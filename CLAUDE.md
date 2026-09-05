# Branch map — read this before changing anything

## `cf-live` is production. It is GENERATED now — do not hand-edit it.

Cloudflare Pages serves `cf-live` **verbatim** at https://www.cochinwood.in, and what
is committed there is exactly what a visitor receives. Both of those are still true,
and most of this file is still good.

**What changed on 4 September 2026, and what this section used to say.** It read:
*"There is no build step, no generator, no package manager, no `dist/`. You edit the
`.html` files directly."* That was true when written and is false now. `cf-live` is
the **output** of `python build.py`, published at commit `ebc11445` —
*"Publish the reviewed build (ce24ab15) as the served tree"*. Editing a `.html` file
on it gets overwritten by the next build.

**The source is `content/` + `build.py` on `cutover-ready-2026-09-04`.** Work there,
build, and publish the result. Verify all of that by counting rather than by trusting
this paragraph:

    git log -1 --format='%h %ad %s' ebc11445             # the cutover
    git ls-tree -r --name-only origin/cf-live | wc -l    # 607, and 253 .html
    git checkout cutover-ready-2026-09-04 && python build.py   # "files: 607"

Verified 2026-08-15, and still the reason not to "fix" a diff you will see: the live
homepage is byte-identical to `index.html` on `cf-live` apart from Cloudflare's own
edge injection — it rewrites `mailto:` links into `/cdn-cgi/l/email-protection` and
adds `email-decode.min.js`. That difference is Cloudflare's, not ours.

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
| `cf-live` | **Production.** The build's output — 607 files, 253 `.html` — served verbatim. Do not hand-edit. | **yes — production** |
| `cutover-ready-2026-09-04` | **The source.** `content/` + `build.py`. This is where work goes. | no — via a build |
| `master` | The original SSG rebuild, now an ancestor of the source branch. Behind. | no |
| `dedupe-2026-08-27` | This branch. A feature branch from 31 Aug, kept because the local `cochinwood-web` checkout sits on it. | no |

Work landed on `master` still reaches no users, and now it is not the successor either.

**`cf-live` has run ahead of the source.** Four pull requests (#17–#20) landed
export-market data directly on `cf-live` after the cutover, and that work is **not**
on `cutover-ready-2026-09-04` — its copies of those files still read `[TO CONFIRM]`
where production carries sourced duty and VAT figures. `build.py` is pinned to
`LIVE_SHA = c59adae9` and carries 311 files from it, so a build published today would
put the older snapshot over them. That is the first of the build's three standing
warnings. Read it before you build, and do not move `LIVE_SHA` without re-reviewing
what landed in between.

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

    API   /zones/<zone>/settings/email_obfuscation   value "off"
                                                     modified_on 2026-08-28T09:11:57Z

    live /            __cf_email__ 0   email-protection 0   plain mailto 3
    live /contact     __cf_email__ 0   email-protection 0   plain mailto 7
    live /llms        __cf_email__ 0   email-protection 0   plain mailto 4
    source            __cf_email__ 0   email-decode.min.js 2

Live and source agree, which is how we know these tags are **ours** — committed into the HTML,
almost certainly fossilised from a Cloudflare pass years ago the same way the Zoho strings were —
rather than injected fresh on each request.

**The live page lags the setting, and on 28 Aug that lag produced a confident wrong answer.** The
switch was thrown at 09:11:57Z. A review measuring the served pages afterwards found `__cf_email__`
on `/`, `/contact` and `/llms`, and reported that the 292-page decode sweep was inert — because the
edge was still serving copies cached *before* the flip. The homepage entry was nearly two hours old.
The origin was correct, the markup was correct, the setting was correct, and the served bytes were
stale, so every check except the setting itself agreed on the wrong answer.

Add `?cb=<random>` to force a MISS if you must read this off a page. But the page is the symptom and
the setting is the fact, which is why the check below is an API call and not a curl.

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

## `/woods-we-use` keeps its URL — decided 31 Aug 2026 by Edwin. Do not re-open.

**The wood section stays at `/woods-we-use`. `/wood-encyclopedia` does NOT become the
canonical path.** It may be renamed *Wood Encyclopedia* in navigation, headings and page
titles — the visible words are free to change, the address is not.

Reason: the live URL is already indexed. Moving it costs a ranking dip and a fresh set of
301s for no product gain, while the naming benefit is available for nothing by changing the
words on the page. Renaming is reversible; losing rankings is not. **Generalise it: when in
doubt, do not move a URL.**

This closes a conflict the 25 Aug audit raised and deliberately left open — blocker 2 and
recommendation 3 in `cochinwood-audit-2026-08-25/CUTOVER-ASSESSMENT.md`, in the shared
workspace repo (`Claude Code`). The two sides were:

- `cf-live` serves one page, `woods-we-use.html`, and `_redirects` lines 28–29 send the
  other name to it:

      /wood-encyclopedia /woods-we-use 301
      /wood-encyclopedia/* /woods-we-use 301

- `master`'s `build.py` builds the opposite — a whole section at the redirected path.
  `build.py:598` writes `wood-encyclopedia/index.html`; `build.py:604` writes
  `wood-encyclopedia/<slug>/index.html` for the 20 species listed at `build.py:590`;
  `build.py:224` puts `("Wood Encyclopedia", "/wood-encyclopedia/", False)` in the nav.
  It emits no `/woods-we-use` page at all.

So `master` is the side that is wrong, and **the generator changes, not the live URL.**

**That code change has NOT been made.** It is a real change with consequences and needs its
own review, so until it lands `build.py` still contradicts this section — that is known, not
an oversight. Whoever picks it up: the target is `/woods-we-use` as the canonical path with
the *Wood Encyclopedia* label kept, and two more things fall out of it —

- `build.py:857-859` regenerates `_redirects` wholesale from `LEGACY_REDIRECTS`: 19 rules
  against the 96 live on `cf-live`, and the map at `build.py:28-48` does not contain the two
  `/wood-encyclopedia` rules above. Cutting over as written replaces the live redirect file
  with the short one and drops them.
- `LEGACY_REDIRECTS` at `build.py:45-47` points three old `/blogs/post/wood-*` slugs at
  `/wood-encyclopedia/...`; those targets have to move too.

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

**Two more cards in that skill are stale the same way, found 5 Sep 2026.** It says
*"50+ countries"* and describes CWI as a *"vertically-integrated manufacturer"*. The
audit settled both the other way and the site now says otherwise:

- **28 countries**, not 50+. The old figure was removed as unsupported.
- The manufacturer answer is `/company-verification`'s: Cochin Wood Industries is the
  selling and exporting entity, registered with FIEO as a **merchant exporter**;
  depending on grade and volume an order is pressed at the group's own unit at
  Perumbavoor, which makes the bulk of what we sell, with some grades and overflow
  from approved mills in the same cluster. The producing unit is named on every
  quotation. Phrases like *"the industries we own"* were removed for this reason.

Same rule as the continents card: **the site is the authority, the skill loses.** When
they disagree, check `/company-verification` and fix the skill, not the page.

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
