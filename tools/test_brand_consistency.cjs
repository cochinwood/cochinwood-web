// Check rendered brand primitives across the canonical site, using local Chrome.
// External requests and all submissions are blocked; no customer records are made.
'use strict';
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = process.env.CWI_TEST_ORIGIN || 'http://127.0.0.1:8873';
assert(['127.0.0.1', 'localhost'].includes(new URL(origin).hostname));
const dist = path.join(__dirname, '../dist');
const routes = new Set();
for (const file of fs.readdirSync(dist).filter(n => /^sitemap.*\.xml$/.test(n))) {
  for (const match of fs.readFileSync(path.join(dist, file), 'utf8').matchAll(/<loc>(https:\/\/www\.cochinwood\.in[^<]*)<\/loc>/g)) {
    const url = new URL(match[1]);
    if (!url.pathname.endsWith('.xml')) routes.add(url.pathname);
  }
}
const narrow = ['/', '/products', '/industries', '/export', '/blogs', '/woods-we-use',
  '/about', '/contact', '/faq', '/privacy-policy', '/terms-and-conditions',
  '/commercial-plywood', '/plywood-factory', '/blogs/post/case-studies'];
const tasks = [...routes].map(route => ({route, width:1440})).concat(narrow.map(route => ({route, width:390})));
(async () => {
  const browser = await chromium.launch({headless:true, channel:'chrome'});
  const records = [], failures = [];
  async function worker() {
    const context = await browser.newContext({serviceWorkers:'block', reducedMotion:'reduce'});
    await context.route('**/*', route => {
      const request = route.request();
      return new URL(request.url()).origin === origin && request.method() === 'GET'
        ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    while (tasks.length) {
      const task = tasks.shift();
      try {
        await page.setViewportSize({width:task.width, height:900});
        const response = await page.goto(origin + task.route, {waitUntil:'load'});
        assert.equal(response.status(), 200);
        await page.evaluate(() => document.fonts.ready);
        const styles = await page.evaluate(() => {
          const read = selector => [...document.querySelectorAll(selector)].map(node => {
            const style = getComputedStyle(node);
            return {text:node.textContent.trim().slice(0,80), font:style.fontFamily,
              weight:style.fontWeight, size:parseFloat(style.fontSize), radius:style.borderRadius};
          });
          return {headings:read('main h1,main h2,main h3,main h4'),
            actions:read('main .cwp__btn,main .cwg__btn,main .cw__btn,main .cwf__btn,main .cw-btn,main .cx-button'),
            rootSize:parseFloat(getComputedStyle(document.documentElement).fontSize),
            overflow:document.documentElement.scrollWidth > innerWidth + 1,
            fontLoaded:document.fonts.check('16px Poppins')};
        });
        assert(styles.fontLoaded, 'Brand font failed to load');
        assert(!styles.overflow, 'Horizontal page overflow');
        for (const heading of styles.headings) {
          assert(heading.font.startsWith('Poppins'), 'Legacy heading font: ' + heading.text);
          assert.equal(heading.weight, '500', 'Heading weight: ' + heading.text);
        }
        for (const action of styles.actions) {
          assert(action.font.startsWith('Poppins'), 'Action font: ' + action.text);
          assert.equal(action.weight, '500', 'Action weight: ' + action.text);
          assert.equal(action.radius, '2px', 'Action shape: ' + action.text);
          assert(Math.abs(action.size - styles.rootSize * .875) < .1, 'Action size: ' + action.text);
        }
        records.push({...task, headings:styles.headings.length, actions:styles.actions.length});
      } catch (error) { failures.push({...task, error:error.message}); }
    }
    await context.close();
  }
  await Promise.all([worker(), worker(), worker(), worker()]);
  await browser.close();
  const result = {passed:failures.length === 0, canonicalRoutes:routes.size,
    checks:records.length + failures.length, failures, records};
  if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify(result, null, 2));
  console.log(JSON.stringify({passed:result.passed, routes:routes.size, checks:result.checks, failures}));
  if (failures.length) process.exitCode = 1;
})().catch(error => {console.error(error); process.exitCode = 1;});
