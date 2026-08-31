# Cloudflare Pages cutover — step-by-step runbook

The whole site is built and verified. This is the final production cutover for
`cochinwood.in`. It has **one interactive step I can't do headlessly** — the
production-branch change in the Cloudflare dashboard (step 5).

> **Rollback corrected 2026-08-31 — there is no DNS step and no Zoho fallback.**
> This paragraph used to read: *"Zoho stays fully live until step 5, so rollback at any point
> is a single DNS change."* **Both halves are false, and following it in an incident would
> point `cochinwood.in` at nothing.** Zoho Sites is gone. `cochinwood.in` and
> `www.cochinwood.in` are already custom domains on the Cloudflare Pages project
> `cochinwood-web`, which serves the `cf-live` branch verbatim — so the domain has no origin
> to "revert" to.
>
> **The rollback is: set the Pages production branch back to `cf-live`, clear the build
> command, restore output directory `/`, redeploy.** Full detail in step 5. DNS is never
> touched, and the custom domains are never removed.
>
> Verified 2026-08-31: `cochinwood.in` 301s to `https://www.cochinwood.in/`, which returns
> 200 from `Server: cloudflare` carrying the enforced CSP that only `cf-live`'s `_headers`
> defines, and `/wood-encyclopedia` 301s to `/woods-we-use` exactly as `cf-live`'s
> `_redirects` specifies.

## 0. Pre-flight (done)
- ✅ Repo `cochinwood/cochinwood-web`, `master` = source, builds with `python build.py`.
- ✅ Quote form posts to CWI's own Worker (`https://www.cochinwood.in/web-lead` → `webLead` in
  `cochin-wood-document-studio/webapp/api-worker.js`), exactly as the live site does, gated by
  Cloudflare Turnstile. **It must never be pointed back at the CRM webform.** That subscription is
  cancelled on 3 September; a form posting there shows the buyer a success page while the enquiry
  reaches nobody. This line claimed the opposite until 31 Aug 2026 — the build really did still
  carry the old CRM form, and this checklist marked it ✅.
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

## 3. Add the custom domain — ✅ done
- ✅ `cochinwood.in` and `www.cochinwood.in` are already attached as custom domains on the
  Pages project `cochinwood-web`. **Nothing to do in this step.**
- Confirmed live 2026-08-31: apex 301s to `https://www.cochinwood.in/`; `www` returns 200;
  both served by `Server: cloudflare` with `cf-live`'s `_headers` CSP.
- ⚠️ **Do not remove these custom domains to roll back.** That takes the site offline — it
  does not fall back to anything. See the rollback in step 5.

## 4. Update `returnURL` on the form (optional)
The quote form's `returnURL` currently points to the live Zoho contact page — fine
during transition. No change needed; it resolves to whatever serves `cochinwood.in`.

## 5. Flip production to the built site  *(you authorize)*

> Corrected 2026-08-26. This step used to say the flip "takes the site off Zoho", and that
> rollback meant removing the custom domain or reverting DNS. **Neither is true any more.**
> `cochinwood.in` and `www` are already custom domains on the Pages project `cochinwood-web`,
> which today serves the `cf-live` branch verbatim. Removing the custom domain would take the
> site *offline*, not back to Zoho. The real flip changes what that project builds.

- Record the current production settings first: branch `cf-live`, **no** build command, output
  directory `/`.
- Change the production branch to `master`, build command `python build.py`, output `dist`.
  Custom domains untouched; DNS untouched.
- Confirm apex + www both serve the new build, then **purge the Cloudflare cache**. Some edge
  PoPs keep serving cached HTML briefly — append a cache-busting query to see what the origin
  is really returning.
- **Rollback:** set the production branch back to `cf-live`, clear the build command, restore
  output `/`, redeploy. `cf-live` is never modified by the cutover, so rolling back returns
  byte-for-byte the site that was live beforehand. Do not remove the custom domain.

## 6. Post-cutover
- Resubmit `sitemap.xml` in Google Search Console.
- Submit a Zoho **test lead** through the live quote form; confirm it lands in CRM.
- Keep Zoho Sites content frozen (don't edit there anymore); all future edits are `git push`.

## What I can do vs. you
- **I can:** build/verify, generate a `cf-live` prebuilt branch if needed, verify the
  pages.dev + custom-domain builds, purge cache (with the CF token), run the test-lead check.
- **You must:** authorize the production-branch change in step 5 — that is the only
  interactive step left. Step 1's GitHub↔Cloudflare OAuth and step 3's custom domains are
  already done, and **no step in this runbook changes DNS.**
