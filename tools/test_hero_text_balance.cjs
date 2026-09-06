// Actual local rendering: one centered desktop group, original mobile order.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.argv[2] || 'http://127.0.0.1:8873';
const origin = new URL(base).origin;
assert(['localhost', '127.0.0.1'].includes(new URL(base).hostname));

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  try {
    const context = await browser.newContext({ serviceWorkers: 'block' });
    await context.route('**/*', route => route.request().method() === 'GET' && new URL(route.request().url()).origin === origin
      ? route.continue() : route.abort());
    const page = await context.newPage();
    for (const width of [390, 887, 1229]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 584 });
      for (const route of ['/products', '/industries', '/export', '/blogs', '/contact']) {
        await page.goto(base + route);
        await page.evaluate(() => document.fonts.ready);
        const result = await page.evaluate(() => {
          const find = name => document.querySelector('.cw-page-hero__' + name);
          const rect = name => { const r = find(name).getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height }; };
          return { grouped: find('heading').parentElement === find('text') && find('support').parentElement === find('text'),
            text: rect('text'), media: rect('media'), heading: rect('heading'), support: rect('support'),
            overflow: document.documentElement.scrollWidth > innerWidth + 1 };
        });
        assert(result.grouped, route);
        assert(!result.overflow, route);
        if (width > 760) {
          assert(Math.abs((result.text.top + result.text.bottom) / 2 - (result.media.top + result.media.bottom) / 2) < 2, route);
          assert(Math.abs(result.support.top - result.heading.bottom) < 2, route);
        } else {
          assert(result.heading.bottom <= result.media.top + 1, route);
          assert(result.media.bottom <= result.support.top + 1, route);
        }
      }
    }
    console.log('15 hero balance cases PASS: grouped centering, intact mobile order and no overflow');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
