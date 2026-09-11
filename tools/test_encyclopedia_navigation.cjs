// Isolated local-only reference navigation checks; never uses a customer session.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const base = process.argv[2] || 'http://127.0.0.1:8873';
const origin = new URL(base).origin;
assert(['127.0.0.1', 'localhost'].includes(new URL(base).hostname));

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  async function context(javaScriptEnabled = true) {
    const ctx = await browser.newContext({ javaScriptEnabled, serviceWorkers: 'block' });
    await ctx.route('**/*', route => {
      const request = route.request();
      return new URL(request.url()).origin === origin && request.method() === 'GET'
        ? route.continue() : route.abort();
    });
    return ctx;
  }
  try {
    const ctx = await context();
    const page = await ctx.newPage();
    await page.goto(base + '/woods-we-use');
    assert.equal(await page.locator('[data-wood-card]').count(), 28);
    const names = await page.locator('.cw-wood-az a').allTextContents();
    assert.equal(names.length, 28);
    assert.deepEqual(names, [...names].sort((a, b) => a.toLowerCase() < b.toLowerCase() ? -1 : 1));
    const urls = await page.locator('.cw-wood-az a').evaluateAll(links => links.map(a => new URL(a.href).pathname));
    assert.equal(new Set(urls).size, 28);

    // Botanical search composes with categories and survives a reload.
    await page.locator('[data-wood-filter="veneer"]').click();
    assert.equal(await page.locator('[data-wood-card]:visible').count(), 11);
    await page.locator('#cw-wood-search').fill('Aucoumea');
    await page.waitForFunction(() => new URL(location.href).searchParams.get('q') === 'Aucoumea');
    assert.equal(await page.locator('[data-wood-card]:visible').count(), 1);
    assert.equal(new URL(page.url()).searchParams.get('group'), 'veneer');
    assert.equal(new URL(page.url()).hash, '#wood-browse');
    await page.reload();
    assert.equal(await page.locator('#cw-wood-search').inputValue(), 'Aucoumea');
    assert.equal(await page.locator('[data-wood-card]:visible').count(), 1);
    await page.locator('[data-wood-filter="packing"]').click();
    assert(await page.locator('#cw-wood-empty').isVisible());
    await page.locator('#cw-wood-clear').click();
    assert.equal(await page.locator('[data-wood-card]:visible').count(), 28);
    assert(!new URL(page.url()).searchParams.has('q'));
    assert(!new URL(page.url()).searchParams.has('group'));
    await page.goto(base + '/woods-we-use?group=unknown&q=okoume');
    assert.equal(await page.locator('[data-wood-card]:visible').count(), 1);

    // A species returns to its category; section links land on actual headings.
    await page.goto(base + '/woods-we-use/okoume');
    await page.locator('.cw-species-context a').nth(1).click();
    await page.waitForFunction(() => document.querySelector('[data-wood-filter="veneer"]')?.getAttribute('aria-current') === 'true');
    assert.equal(new URL(page.url()).searchParams.get('group'), 'veneer');
    assert.equal(await page.locator('[data-wood-card]:visible').count(), 11);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(base + '/woods-we-use/okoume');
    const toc = page.locator('nav[aria-label="On this page"]');
    const enclosingDetails = toc.locator('xpath=ancestor::details');
    if (await enclosingDetails.count()) await enclosingDetails.locator('summary').click();
    const first = toc.locator('a').first();
    const target = await first.getAttribute('href');
    await first.click();
    assert.equal(new URL(page.url()).hash, target);
    await ctx.close();

    // Native category links and A-Z/details remain usable with JavaScript off.
    const native = await context(false);
    const nativePage = await native.newPage();
    await nativePage.setViewportSize({ width: 390, height: 844 });
    await nativePage.goto(base + '/woods-we-use');
    assert.equal(await nativePage.locator('[data-wood-card]:visible').count(), 28);
    await nativePage.locator('.cw-wood-az summary').click();
    assert.equal(await nativePage.locator('.cw-wood-az a:visible').count(), 28);
    await nativePage.locator('[data-wood-filter="indian"]').click();
    assert.equal(new URL(nativePage.url()).hash, '#wood-group-indian');
    await nativePage.goto(base + '/woods-we-use');
    await nativePage.locator('.cw-wood-az summary').click();
    await nativePage.locator('.cw-wood-az a').first().click();
    assert.equal(new URL(nativePage.url()).pathname, urls[0]);
    await native.close();

    // Every alphabetical neighbour and TOC target, at phone/tablet/desktop widths.
    const failures = [];
    let checked = 0;
    const audit = await context();
    const auditPage = await audit.newPage();
    for (const width of [320, 390, 768, 1024, 1440]) {
      await auditPage.setViewportSize({ width, height: 900 });
      for (const url of ['/woods-we-use', ...urls]) {
        const response = await auditPage.goto(base + url);
        assert.equal(response.status(), 200);
        const errors = await auditPage.evaluate(() => {
          const errors = [];
          if (document.documentElement.scrollWidth > innerWidth + 1) errors.push('horizontal overflow');
          const ids = [...document.querySelectorAll('[id]')].map(n => n.id);
          if (new Set(ids).size !== ids.length) errors.push('duplicate IDs');
          for (const link of document.querySelectorAll('nav[aria-label="On this page"] a')) {
            if (!document.getElementById(decodeURIComponent(link.hash.slice(1)))) errors.push('missing TOC target');
          }
          return errors;
        });
        if (url !== '/woods-we-use') {
          const i = urls.indexOf(url);
          const expected = [urls[i - 1], urls[i + 1]].filter(Boolean);
          const actual = await auditPage.locator('.cw-species-neighbours a').evaluateAll(links => links.map(a => new URL(a.href).pathname));
          assert.deepEqual(actual, expected, url);
        }
        if (errors.length) failures.push({ width, url, errors });
        checked++;
      }
    }
    await audit.close();
    console.log(JSON.stringify({ species: 28, layoutChecks: checked, failures }));
    assert.equal(failures.length, 0);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
