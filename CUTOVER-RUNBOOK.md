# Cloudflare Pages cutover — step-by-step runbook

The whole site is built and verified. This is the final production cutover for
`cochinwood.in`. It has **two interactive steps only I can't do headlessly**
(a dashboard OAuth and the DNS flip). Zoho stays fully live until step 5, so
rollback at any point is a single DNS change.

## 0. Pre-flight (done)
- ✅ Repo `cochinwood/cochinwood-web`, `master` = source, builds with `python build.py`.
- ✅ Quote form posts directly to Zoho CRM (`crm.zoho.in/crm/WebToLeadForm`) — no server needed.
- ✅ `_headers` (security + font caching), `sitemap.xml`, `robots.txt`, Org/BlogPosting schema.

## 1. Create the Cloudflare Pages project  *(you, in the Cloudflare dashboard)*
1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Authorize the **`cochinwood` GitHub** account (one-time OAuth), pick repo **cochinwood-web**.
3. Build settings — **RECOMMENDED (no-build, guaranteed): use the prebuilt branch**
   - Production branch: **`cf-live`**   ← prebuilt, already pushed
   - Framework preset: **None**
   - **Build command:** *(leave empty)*
   - **Build output directory:** `/`
4. **Save and Deploy.** You get a `https://cochinwood-web.pages.dev` URL to verify.

> The `cf-live` branch already contains the finished site (root-relative links), so
> Cloudflare just serves it — nothing to build. When the site changes, I regenerate
> and re-push `cf-live`.
>
> *(Alternative, auto-rebuild on push: production branch `master`, build command
> `python build.py`, output dir `dist`. Only use if you want CF to rebuild from
> source — the prebuilt branch is simpler and can't fail on the build step.)*

## 2. Verify the `*.pages.dev` build
- Spot-check home, a product page, a blog post, the encyclopedia, `/sitemap.xml`, the quote form.
- (I can run this verification for you against the pages.dev URL.)

## 3. Add the custom domain  *(you, in the Pages project)*
1. Pages project → **Custom domains** → **Set up a custom domain** → `cochinwood.in`, then `www.cochinwood.in`.
2. Cloudflare auto-creates the CNAME/route because DNS is already on Cloudflare.

## 4. Update `returnURL` on the form (optional)
The quote form's `returnURL` currently points to the live Zoho contact page — fine
during transition. No change needed; it resolves to whatever serves `cochinwood.in`.

## 5. Flip production to Pages  *(you authorize — takes the site off Zoho)*
- In Cloudflare, the custom-domain attach routes `cochinwood.in` to the Pages project.
- Confirm the apex + www both serve the new site; then **purge the Cloudflare cache**.
- **Rollback:** remove the custom domain from Pages (or revert the DNS/route) → back to Zoho instantly.

## 6. Post-cutover
- Resubmit `sitemap.xml` in Google Search Console.
- Submit a Zoho **test lead** through the live quote form; confirm it lands in CRM.
- Keep Zoho Sites content frozen (don't edit there anymore); all future edits are `git push`.

## What I can do vs. you
- **I can:** build/verify, generate a `cf-live` prebuilt branch if needed, verify the
  pages.dev + custom-domain builds, purge cache (with the CF token), run the test-lead check.
- **You must:** the GitHub↔Cloudflare OAuth (step 1) and authorizing the domain/DNS flip (steps 3, 5).
