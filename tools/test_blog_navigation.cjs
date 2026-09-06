// Local-only blog behavior and responsive regression checks. Never uses a user profile.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const base = process.argv[2] || 'http://127.0.0.1:8873';
const origin = new URL(base).origin;
assert(['127.0.0.1', 'localhost'].includes(new URL(base).hostname));

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  let checked = 0;

  // Only local read requests are allowed, including in the no-JS context.
  async function context(javaScriptEnabled = true) {
    const ctx = await browser.newContext({ javaScriptEnabled, serviceWorkers: 'block' });
    await ctx.route('**/*', route => {
      const request = route.request();
      return new URL(request.url()).origin === origin && request.method() === 'GET'
        ? route.continue()
        : route.abort();
    });
    return ctx;
  }

  try {
    const ctx = await context();
    const page = await ctx.newPage();

    // Topic and text filters compose, survive reload, and clear together.
    await page.goto(base + '/blogs');
    const total = await page.locator('.cw-bloglist > a').count();
    assert(total > 100);
    await page.locator('[data-blog-topic-filter="buying-guides"]').click();
    assert.equal(new URL(page.url()).searchParams.get('topic'), 'buying-guides');
    assert.equal(await page.locator('.cw-bloglist > a:visible').count(), 4);
    await page.locator('#cw-blogsearch').fill('factory');
    await page.waitForFunction(() => new URL(location.href).searchParams.get('q') === 'factory');
    assert.equal(new URL(page.url()).searchParams.get('q'), 'factory');
    assert.equal(new URL(page.url()).hash, '#articles');
    const hits = await page.locator('.cw-bloglist > a:visible').count();
    assert(hits > 0 && hits < 4);
    await page.reload();
    assert.equal(await page.locator('#cw-blogsearch').inputValue(), 'factory');
    assert.equal(await page.locator('.cw-bloglist > a:visible').count(), hits);
    await page.locator('#cw-blogsearch').fill('zzzz-no-such-guide');
    await page.locator('#cw-blogempty').waitFor({ state: 'visible' });
    assert(await page.locator('#cw-blogempty').isVisible());
    await page.locator('#cw-blogclear').click();
    assert.equal(await page.locator('.cw-bloglist > a:visible').count(), total);
    assert(!new URL(page.url()).searchParams.has('q'));
    assert(!new URL(page.url()).searchParams.has('topic'));
    await page.goto(base + '/blogs?topic=invalid&q=marine');
    assert(await page.locator('.cw-bloglist > a:visible').count() > 0);
    const articles = await page.locator('.cw-bloglist > a').evaluateAll(
      elements => elements.map(element => new URL(element.href).pathname)
    );

    // Article navigation returns to its topic; mobile contents use native details.
    await page.goto(base + '/blogs/post/case-studies');
    assert(await page.locator('.cw-article-back').count() > 0);
    await page.locator('.cw-article-topic').first().click();
    assert.equal(new URL(page.url()).searchParams.get('topic'), 'buying-guides');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(base + '/blogs/post/case-studies');
    const details = page.locator('details.cw-article-toc');
    assert(await details.isVisible());
    await details.locator('summary').click();
    assert(await details.getAttribute('open') !== null);
    const href = await details.locator('a').first().getAttribute('href');
    await details.locator('a').first().click();
    assert.equal(new URL(page.url()).hash, href);

    // Shared navigation and the existing quote endpoint remain intact.
    await page.goto(base + '/contact');
    assert.equal(await page.locator('form').getAttribute('action'), 'https://www.cochinwood.in/web-lead');
    await page.locator('.cw-burger').click();
    assert.equal(await page.locator('.cw-burger').getAttribute('aria-expanded'), 'true');
    await page.locator('#nav a[href="/products"]').click();
    assert.equal(new URL(page.url()).pathname, '/products');
    await ctx.close();

    // No JavaScript: every article remains visible and native links/details work.
    const noJs = await context(false);
    const nativePage = await noJs.newPage();
    await nativePage.setViewportSize({ width: 390, height: 844 });
    await nativePage.goto(base + '/blogs');
    assert.equal(await nativePage.locator('.cw-bloglist > a:visible').count(), total);
    await nativePage.locator('[data-blog-topic-filter="buying-guides"]').click();
    assert.equal(new URL(nativePage.url()).hash, '#blog-topic-buying-guides');
    await nativePage.goto(base + '/blogs/post/case-studies');
    await nativePage.locator('details.cw-article-toc summary').click();
    assert(await nativePage.locator('details.cw-article-toc').getAttribute('open') !== null);
    await noJs.close();

    // Every article and the index at five widths; four isolated pages share a queue.
    const tasks = [320, 390, 768, 1024, 1440].flatMap(width =>
      ['/blogs', ...articles].map(url => ({ width, url }))
    );
    const failures = [];
    async function worker() {
      const workerContext = await context();
      const workerPage = await workerContext.newPage();
      while (tasks.length) {
        const task = tasks.shift();
        try {
          await workerPage.setViewportSize({ width: task.width, height: 900 });
          await workerPage.goto(base + task.url);
          const issues = await workerPage.evaluate(() => {
            const errors = [];
            if (document.documentElement.scrollWidth > innerWidth + 1) {
              errors.push('horizontal overflow');
            }
            const ids = [...document.querySelectorAll('[id]')].map(element => element.id);
            if (new Set(ids).size !== ids.length) errors.push('duplicate IDs');
            for (const anchor of document.querySelectorAll('.cw-article-toc a')) {
              const id = decodeURIComponent(anchor.hash.slice(1));
              if (!id || (document.querySelectorAll('[id]').length && !document.getElementById(id))) {
                errors.push('missing TOC target ' + id);
              }
            }
            for (const anchor of document.querySelectorAll('.cw-article-related a')) {
              if (new URL(anchor.href).pathname === location.pathname) errors.push('self-related link');
            }
            return errors;
          });
          if (issues.length) failures.push({ ...task, issues });
        } catch (error) {
          failures.push({ ...task, error: error.message.slice(0, 120) });
        }
        checked++;
      }
      await workerContext.close();
    }
    await Promise.all(Array.from({ length: 4 }, worker));
    console.log(JSON.stringify({ behavior: 'PASS', articles: articles.length, layoutChecks: checked, failures }));
    assert.equal(failures.length, 0);
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error.stack);
  process.exitCode = 1;
});

