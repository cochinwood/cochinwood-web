// Read-only local regression audit; requires the integrated dist/ to be served.
// Usage: node tools/test_hero_consistency.cjs [http://127.0.0.1:8873] [report.json]
// NODE_PATH may point to bundled Playwright. Uses isolated installed Chrome.
// It never submits forms or allows nonlocal requests. Shared image stages and
// gutters are fixed by contract; hero height grows naturally with actual content.
'use strict';

const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const origin = new URL(process.argv[2] || 'http://127.0.0.1:8873');
assert(['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname), 'Loopback origin required');
assert(['http:', 'https:'].includes(origin.protocol), 'HTTP(S) origin required');
assert(!origin.username && !origin.password && origin.pathname === '/', 'Use a bare loopback origin');

// 640 CSS pixels also checks 200% reflow from a 1280-pixel desktop viewport.
const WIDTHS = [320, 390, 640, 768, 887, 1100, 1440, 1920];
const MAIN_ROUTES = ['/products', '/industries', '/export', '/blogs', '/woods-we-use', '/about', '/contact'];
const PRODUCT_SLUGS = [
  'packing-plywood', 'okoume-plywood', 'rubberwood-plywood', 'commercial-plywood',
  'marine-plywood', 'film-faced-shuttering-plywood', 'container-flooring-plywood',
  'bwr-hardwood-plywood', 'chequered-anti-skid-plywood', 'plywood-boxes-crates',
  'plywood-pallets', 'block-board-flush-doors', 'finger-joint-board',
  'particle-board', 'plywood-cable-drums', 'sawn-timber',
];
const TIMBER_LABELS = ['Eucalyptus', 'Rubberwood', 'Acacia', 'Mahogany', 'Jackwood', 'Silverwood', 'Specialty timbers'];
const EXPECTED_IMAGES = {
  '/products': '/files/Hero Optimized/Products.jpg',
  '/blogs': '/files/Brand/home-materials.webp',
  '/woods-we-use': '/files/Product/specialty-timbers.jpg',
  '/sawn-timber': '/files/Product/acacia.jpg',
  '/container-flooring-plywood': '/files/Logo/og/og-container-flooring.jpg',
  '/export': '/files/Process Illustrations/cwi-process-loading.jpg',
};
const responsive = JSON.parse(fs.readFileSync(path.join(__dirname, '../content/responsive-media.json'), 'utf8'));
const normalizedPath = value => decodeURIComponent(new URL(value, origin).pathname);
const sceneCandidates = new Map(Object.entries(responsive).map(([source, candidates]) => [
  normalizedPath(source), new Set(candidates.map(candidate => normalizedPath(candidate.src))),
]));

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted.length % 2 ? sorted[(sorted.length - 1) / 2]
    : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2;
}

(async () => {
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const failures = [], review = [], metrics = [], blocked = new Map();
  const tasks = WIDTHS.flatMap(width => [...MAIN_ROUTES, ...PRODUCT_SLUGS.map(slug => '/' + slug)]
    .map(route => ({width, route})));
  const total = tasks.length;
  let completed = 0;

  async function worker() {
    const context = await browser.newContext({
      serviceWorkers: 'block', reducedMotion: 'reduce', acceptDownloads: false,
    });
    await context.route('**/*', request => {
      const url = new URL(request.request().url());
      if (url.origin === origin.origin && request.request().method() === 'GET') return request.continue();
      const key = request.request().method() + ' ' + url.origin;
      blocked.set(key, (blocked.get(key) || 0) + 1);
      return request.abort('blockedbyclient');
    });
    const page = await context.newPage();
    try {
      while (tasks.length) {
        const task = tasks.shift();
        try {
          await page.setViewportSize({width: task.width, height: 1000});
          // Wait for the stylesheet load before document.fonts.ready; otherwise
          // the FontFaceSet can resolve before deferred CSS declares its fonts.
          const response = await page.goto(new URL(task.route, origin).href, {waitUntil: 'load', timeout: 25000});
          assert(response && response.status() === 200, `HTTP ${response && response.status()}`);
          await page.evaluate(() => document.fonts.ready);
          const hero = page.locator('main .cw-page-hero');
          assert.equal(await hero.count(), 1, 'Exactly one semantic .cw-page-hero required');
          await hero.waitFor({state: 'visible', timeout: 10000});

          // Trigger local lazy assets without scrolling or modifying page layout.
          // This is only a decode/integrity check, not a page-speed measurement.
          const brokenImages = await page.locator('main img').evaluateAll(images => Promise.all(images.map(img => new Promise(resolve => {
            let done = false;
            const finish = error => {
              if (done) return;
              done = true;
              clearTimeout(timer);
              img.removeEventListener('load', loaded);
              img.removeEventListener('error', failed);
              resolve(error ? {src: img.getAttribute('src'), currentSrc: img.currentSrc, error} : null);
            };
            const loaded = () => {
              if (!img.naturalWidth) return finish('Image has no decoded pixels');
              if (img.decode) img.decode().then(() => finish(null), () => finish('Image decode failed'));
              else finish(null);
            };
            const failed = () => finish('Image request failed');
            const timer = setTimeout(() => finish('Image did not load within 10 seconds'), 10000);
            img.addEventListener('load', loaded);
            img.addEventListener('error', failed);
            if (img.complete) loaded();
            else img.loading = 'eager';
          }))));
          const broken = brokenImages.filter(Boolean);
          if (broken.length) failures.push({...task, issue: 'Broken main-content images', images: broken});
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));

          const result = await hero.evaluate(el => {
            const round = value => Math.round(value * 100) / 100;
            const box = node => {
              if (!node) return null;
              const r = node.getBoundingClientRect();
              return {left: round(r.left), top: round(r.top + scrollY), right: round(r.right), bottom: round(r.bottom + scrollY), width: round(r.width), height: round(r.height)};
            };
            const visible = node => {
              const s = getComputedStyle(node);
              return s.display !== 'none' && s.visibility !== 'hidden' && node.getClientRects().length > 0;
            };
            const title = el.querySelector('.cw-page-hero__title');
            const inner = el.querySelector('.cw-page-hero__inner');
            const frame = el.querySelector('.cw-page-hero__media');
            const img = frame && frame.querySelector('img');
            const style = title && getComputedStyle(title), innerStyle = inner && getComputedStyle(inner);
            const imageStyle = img && getComputedStyle(img), frameStyle = frame && getComputedStyle(frame);
            const clipped = [];
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            let textNode;
            while ((textNode = walker.nextNode())) {
              if (!textNode.textContent.trim() || !visible(textNode.parentElement)) continue;
              if (textNode.parentElement.closest('script,style')) continue;
              const range = document.createRange();
              range.selectNodeContents(textNode);
              for (const rect of range.getClientRects()) {
                if (rect.width < 1 || rect.height < 1) continue;
                let reason = '';
                if (rect.left < -2 || rect.right > innerWidth + 2) reason = 'Text outside viewport';
                for (let parent = textNode.parentElement; parent && !reason; parent = parent.parentElement) {
                  const s = getComputedStyle(parent), r = parent.getBoundingClientRect();
                  if (/^(hidden|clip)$/.test(s.overflowX) && (rect.left < r.left - 2 || rect.right > r.right + 2)) reason = 'Text clipped horizontally';
                  if (/^(hidden|clip)$/.test(s.overflowY) && (rect.top < r.top - 2 || rect.bottom > r.bottom + 2)) reason = 'Text clipped vertically';
                  if (parent === el) break;
                }
                if (reason) clipped.push({reason, text: textNode.textContent.trim().slice(0, 90), parent: textNode.parentElement.className});
              }
            }
            const heroBox = box(el), titleBox = box(title), frameBox = box(frame), imageBox = box(img);
            const contentOutsideHero = [...el.querySelectorAll('.cw-page-hero__heading,.cw-page-hero__support,.cw-page-hero__media')]
              .filter(visible).map(node => ({className: node.className, ...box(node)}))
              .filter(r => r.left < heroBox.left - 2 || r.right > heroBox.right + 2 || r.top < heroBox.top - 2 || r.bottom > heroBox.bottom + 2);
            const labelledBy = el.getAttribute('aria-labelledby');
            return {
              semanticTag: el.tagName.toLowerCase(), compact: el.classList.contains('cw-page-hero--compact'),
              titleText: title && title.textContent.trim().replace(/\s+/g, ' '), titleTag: title && title.tagName.toLowerCase(),
              labelledBy, validLabel: !!(labelledBy && title && labelledBy.split(/\s+/).includes(title.id)),
              hero: heroBox, minHeight: innerStyle ? parseFloat(innerStyle.minHeight) || 0 : 0,
              inner: box(inner), title: titleBox, frame: frameBox, image: imageBox, viewportHeight:innerHeight,
              expectedGutter: inner && round(inner.getBoundingClientRect().left + parseFloat(innerStyle.paddingLeft)),
              headingFont: style && {family: style.fontFamily, size: style.fontSize, weight: style.fontWeight, style: style.fontStyle, lineHeight: style.lineHeight},
              emphasisFont: title && title.querySelector('em') ? getComputedStyle(title.querySelector('em')).fontFamily : null,
              poppinsReady: document.fonts.check('500 16px Poppins'),
              frameRadius: frameStyle && [frameStyle.borderTopLeftRadius, frameStyle.borderTopRightRadius, frameStyle.borderBottomRightRadius, frameStyle.borderBottomLeftRadius],
              imageRadius: imageStyle && [imageStyle.borderTopLeftRadius, imageStyle.borderTopRightRadius, imageStyle.borderBottomRightRadius, imageStyle.borderBottomLeftRadius],
              objectFit: imageStyle && imageStyle.objectFit, source: img && img.getAttribute('src'), selectedSource: img && img.currentSrc,
              naturalWidth: img && img.naturalWidth, naturalHeight: img && img.naturalHeight,
              pageScrollWidth: document.documentElement.scrollWidth, clipped: clipped.slice(0, 12), contentOutsideHero,
            };
          });
          metrics.push({...task, ...result});
          const fail = (issue, details) => failures.push({...task, issue, ...details});
          if (!['section', 'header'].includes(result.semanticTag) || result.titleTag !== 'h1') fail('Hero must be a section/header with an h1');
          if (!result.title || !result.inner || !result.headingFont) fail('Shared hero structure incomplete');
          if (result.pageScrollWidth > task.width + 2) fail('Horizontal page overflow', {scrollWidth: result.pageScrollWidth});
          if (result.clipped.length || result.contentOutsideHero.length) fail('Hero content clipped or outside its section', {clipped: result.clipped, outside: result.contentOutsideHero});
          if (result.headingFont && !/^['"]?Poppins['"]?(,|$)/i.test(result.headingFont.family)) fail('Heading does not use Poppins', {font: result.headingFont});
          if (!result.poppinsReady) fail('Poppins is not loaded');
          if (result.title && Math.abs(result.title.left - result.expectedGutter) > 2) fail('Title does not align to shared content gutter', {left: result.title.left, expected: result.expectedGutter});
          if (result.labelledBy && !result.validLabel) fail('Hero aria-labelledby does not identify its h1');
          if (!result.compact && !result.image) fail('Image hero is missing its media frame');
          if (result.image) {
            if (task.width <= 760 && Math.abs(result.image.width / result.image.height - 4 / 3) > 0.025) fail('Mobile hero image frame is not 4:3', {image: result.image});
            if (task.width > 760) {
              // The complete figure now shares the height budget, including any
              // caption. Compare frames across pages below; do not require the
              // old image minimum that overflowed shorter Chrome windows.
              if (result.frame.height < 240 || result.frame.height > result.viewportHeight - 100)
                fail('Desktop media stage is too small or exceeds its viewport budget', {frame:result.frame});
              if (result.image.bottom > result.frame.bottom + 2)
                fail('Image extends beyond the shared media stage', {image:result.image,frame:result.frame});
              const usableWidth = result.inner.width - 2 * (result.expectedGutter - result.inner.left);
              const fraction = result.image.width / usableWidth;
              if (fraction < .58 || fraction > .65) fail('Desktop imagery does not occupy the intended large visual share', {fraction, image: result.image, usableWidth});
            }
            if ([...result.frameRadius, ...result.imageRadius].some(radius => parseFloat(radius) > 0.1)) fail('Hero image corners differ from the square shared frame', {frameRadius: result.frameRadius, imageRadius: result.imageRadius});
            if (result.objectFit !== 'cover') fail('Hero image does not use cover sizing', {objectFit: result.objectFit});
          }
          if (EXPECTED_IMAGES[task.route]) {
            const expected = EXPECTED_IMAGES[task.route];
            if (!result.source || normalizedPath(result.source) !== expected) fail('Incorrect hero scene assignment', {expected, actual: result.source});
            const allowed = sceneCandidates.get(expected) || new Set([expected]);
            if (!result.selectedSource || !allowed.has(normalizedPath(result.selectedSource))) fail('Responsive candidate is not from the inspected scene family', {expected, selected: result.selectedSource});
          }
          if (task.route === '/products') {
            const catalogue = await page.evaluate(() => ({
              destinations: [...new Set([...document.querySelectorAll('main a[href]')].map(a => new URL(a.href).pathname))],
              timber: [...document.querySelectorAll('.cw-timber-choice')].map(a => ({label: a.querySelector('h3')?.textContent.trim(), href: new URL(a.href).pathname, images: a.querySelectorAll('img').length})),
              flooringImage: document.querySelector('.cw-product-card[href="/container-flooring-plywood"] img')?.getAttribute('src'),
            }));
            const missing = PRODUCT_SLUGS.filter(slug => !catalogue.destinations.includes('/' + slug));
            if (missing.length) fail('Catalogue is missing product destinations', {missing});
            if (JSON.stringify(catalogue.timber.map(item => item.label)) !== JSON.stringify(TIMBER_LABELS)) fail('Seven ordered timber choices are missing or changed', {timber: catalogue.timber});
            if (catalogue.timber.some(item => item.href !== '/sawn-timber' || item.images !== 1)) fail('Timber choice needs one image and a working sawn-timber destination', {timber: catalogue.timber});
            if (!catalogue.flooringImage || normalizedPath(catalogue.flooringImage) !== EXPECTED_IMAGES['/container-flooring-plywood']) fail('Container-flooring catalogue card uses the wrong scene', {actual: catalogue.flooringImage});
          }
        } catch (error) {
          failures.push({...task, issue: 'Page audit could not complete', error: error.message});
        }
        completed++;
        if (completed % 24 === 0) console.log(`Hero audit: ${completed}/${total} page-width checks complete`);
      }
    } finally {
      await context.close();
    }
  }

  try { await Promise.all([worker(), worker()]); }
  finally { await browser.close(); }

  const heightBands = [];
  for (const width of WIDTHS) {
    const cohort = metrics.filter(item => item.width === width && item.title && !item.compact);
    if (!cohort.length) continue;
    const baseline = cohort.find(item => item.route === '/products') || cohort[0];
    const normalHeight = median(cohort.map(item => item.hero.height));
    const imageWidths = cohort.filter(item => item.image).map(item => item.image.width);
    const normalImageWidth = imageWidths.length ? median(imageWidths) : null;
    heightBands.push({
      viewport: width, min: Math.min(...cohort.map(item => item.hero.height)),
      median: normalHeight, max: Math.max(...cohort.map(item => item.hero.height)),
      catalogueHeight: baseline.hero.height, commonImageWidth: normalImageWidth,
      mainPages: cohort.filter(item => MAIN_ROUTES.includes(item.route))
        .map(item => ({route: item.route, height: item.hero.height})),
      expandedPages: width > 760 ? cohort.filter(item => item.hero.height > item.minHeight + 2)
        .map(item => ({route: item.route, height: item.hero.height, title: item.titleText})) : [],
    });
    for (const item of cohort) {
      if (width > 760 && item.frame && baseline.frame && Math.abs(item.frame.height-baseline.frame.height)>2)
        failures.push({width,route:item.route,issue:'Figure height differs across shared hero family',expected:baseline.frame.height,actual:item.frame.height});
      for (const property of ['family', 'size', 'weight', 'style']) {
        if (item.headingFont[property] !== baseline.headingFont[property]) failures.push({width, route: item.route, issue: 'Heading typography differs across the shared hero family', property, expected: baseline.headingFont[property], actual: item.headingFont[property]});
      }
      if (Math.abs(item.title.left - baseline.title.left) > 2) failures.push({width, route: item.route, issue: 'Hero left gutter differs across pages', expected: baseline.title.left, actual: item.title.left});
      if (item.image && normalImageWidth && Math.abs(item.image.width - normalImageWidth) > 3) review.push({width, route: item.route, issue: 'Hero image width differs from same-viewport median', widthPx: item.image.width, cohortMedian: normalImageWidth});
    }
  }

  const report = {
    origin: origin.origin, checkedAt: new Date().toISOString(), widths: WIDTHS,
    checks: completed, productRoutes: PRODUCT_SLUGS.length, timberChoicesExpected: TIMBER_LABELS.length,
    isolation: 'Fresh headless Chrome contexts; service workers blocked; same-origin GET requests only; reduced motion; no forms submitted.',
    interpretation: 'Typography, gutters, image scenes, missing content, decode errors, clipping, responsive image-stage height and desktop media width share are regression failures. Content-driven hero height may grow; image-width outliers are reported for visual review. The 640px case covers 200% desktop reflow equivalence, not a claim about browser zoom controls.',
    blockedRequests: [...blocked].map(([request, count]) => ({request, count})), failures, review, heightBands,
    metrics: metrics.sort((a, b) => a.width - b.width || a.route.localeCompare(b.route)),
  };
  if (process.argv[3]) {
    const output = path.resolve(process.argv[3]);
    fs.mkdirSync(path.dirname(output), {recursive: true});
    fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
  }
  console.log(JSON.stringify({checks: completed, failures: failures.length, reviewItems: review.length, report: process.argv[3] || null, heightBands, details: failures, review}, null, 2));
  process.exitCode = failures.length ? 1 : 0;
})().catch(error => { console.error(error.stack || error.message); process.exitCode = 1; });
