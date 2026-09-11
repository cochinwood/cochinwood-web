// Isolated local preview only; all nonlocal and mutating requests are blocked.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const base = process.argv[2] || 'http://127.0.0.1:8873';
const origin = new URL(base).origin;
assert(['localhost', '127.0.0.1'].includes(new URL(base).hostname));

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  try {
    const context = await browser.newContext({ serviceWorkers: 'block' });
    await context.route('**/*', route => {
      const request = route.request();
      return request.method() === 'GET' && new URL(request.url()).origin === origin
        ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    const owners = JSON.parse(fs.readFileSync(path.join(__dirname, '../content/unique-imagery.json'), 'utf8')).owners;
    const assets = JSON.parse(fs.readFileSync(path.join(__dirname, '../content/unique-imagery-assets.json'), 'utf8')).assets;
    for (const [route, owner] of Object.entries(owners)) {
      if (owner.status !== 'approved') continue;
      const response = await context.request.get(base + route);
      assert.equal(response.status(), 200);
      const html = await response.text();
      const schema = [...html.matchAll(/<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)]
        .map(match => JSON.parse(match[1])).find(value => value['@type'] === 'BlogPosting');
      assert(schema, route);
      const og = html.match(/property="og:image" content="([^"]+)"/)[1];
      const twitter = html.match(/name="twitter:image" content="([^"]+)"/)[1];
      if (owner.kind === 'text_guide') {
        assert(!Object.hasOwn(schema, 'image'), route);
        assert(og.endsWith('/assets/og/cwi-og-share-1200x630.png'), route);
        assert.equal(twitter, og);
      } else {
        assert(og.endsWith(assets[owner.asset_key].src), route);
        assert.equal(schema.image, og);
        assert.equal(twitter, og);
      }
    }
    for (const width of [390, 1229]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto(base + '/blogs?topic=city-supply&q=tiruppur#articles');
      const visible = page.locator('.cw-bloglist > a:visible');
      assert.equal(await visible.count(), 1);
      assert.equal(await visible.locator('img').count(), 0);
      assert.match(await visible.innerText(), /Tamil Nadu · India/);
      assert.match(await visible.innerText(), /Read supply guide/);
      await page.reload();
      assert.equal(await page.locator('#cw-blogsearch').inputValue(), 'tiruppur');
      assert.equal(await visible.count(), 1);
      await page.locator('#cw-blogclear').click();
      assert.equal(await visible.count(), 157);
      assert.equal(await page.locator('.cw-blog-location-card').count(), 109);
      assert.equal(await page.locator('.cw-blog-location-card img').count(), 0);
      assert.equal(await page.locator('.cw-bloglist > a:not(.cw-blog-location-card) img').count(), 48);
      assert(!new URL(page.url()).searchParams.has('q'));
      assert(!new URL(page.url()).searchParams.has('topic'));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await page.goto(base + '/blogs/post/plywood-supply-to-tiruppur');
      assert.equal(await page.locator('article.cw-reading-content > figure.cw-editorial-media').count(), 0);
      assert(await page.locator('article.cw-reading-content h2').count() > 0);
    }
    console.log('Location preview: mixed157 cards,109 text guides,48 image cards, URL restore/clear, two widths and retained article headings PASS');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
