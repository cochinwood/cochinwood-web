// Isolated local preview only; all nonlocal and mutating requests are blocked.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
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
    await page.goto(base + '/blogs/post/plywood-supply-to-tiruppur');
    const minimumHeading = page.locator('article.cw-reading-content h3').filter({ hasText: 'minimum order to make a truckload' });
    assert.equal(await minimumHeading.count(), 1);
    assert.equal(await minimumHeading.evaluate(node => node.nextElementSibling?.tagName), 'P');

    for (const slug of ['plywood-supply-to-muscat', 'plywood-supply-to-ras-al-khaimah']) {
      await page.goto(base + '/blogs/post/' + slug);
      const tables = page.locator('article.cw-reading-content table');
      assert(await tables.count() > 0, slug);
      for (let index = 0; index < await tables.count(); index += 1) {
        const structure = await tables.nth(index).evaluate(table => ({
          heads: table.querySelectorAll(':scope > thead').length,
          bodies: table.querySelectorAll(':scope > tbody').length,
          nestedHeads: table.querySelectorAll('thead thead').length,
        }));
        assert.deepEqual(structure, { heads: 1, bodies: 1, nestedHeads: 0 }, slug);
      }
    }
    console.log('Rendered blog markup: Tiruppur FAQ and Muscat/RAK table DOM PASS');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
