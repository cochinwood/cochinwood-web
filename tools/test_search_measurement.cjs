// Privacy regression: mocked production origin, no real network or form submissions.
// Run: NODE_PATH=<bundled dependencies> node tools/test_search_measurement.cjs
'use strict';
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const js = fs.readFileSync(path.join(root, 'assets/search-measurement.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'assets/privacy-choices.css'), 'utf8');
const controls = execFileSync('python', ['-c', 'from website_measurement import controls; print(controls(lambda x:x))'], {cwd:root, encoding:'utf8'});
const html = '<!doctype html><html><head><meta name="viewport" content="width=device-width"><title>Cochin Wood quote</title><style>' + css + '</style></head><body><main><h1>Request a quote</h1><form><input name="email" value="private@example.test"><textarea name="description">Private purchase details</textarea></form></main>' + controls + '<script>' + js + '</script></body></html>';
const GOOGLE = 'https://www.googletagmanager.com/gtm.js?id=GTM-K2DJRFM8';
const assertions = [];
function check(value, name) { assert(value, name); assertions.push(name); }
(async () => {
  const browser = await chromium.launch({headless:true, channel:'chrome'});
  async function fixture(url, saved, width = 390, height = 844) {
    const context = await browser.newContext({viewport:{width,height}, serviceWorkers:'block'});
    const requests = [];
    await context.route('**/*', async route => {
      const request = route.request();
      requests.push({url:request.url(), method:request.method()});
      if (request.isNavigationRequest() && request.url() === url.split('#')[0] && request.method() === 'GET') {
        return route.fulfill({status:200, contentType:'text/html', body:html});
      }
      // No external code executes, even after opt-in; inspect only local queue intent.
      return route.fulfill({status:200, contentType:'application/javascript', body:''});
    });
    if (saved) await context.addInitScript(value => localStorage.setItem('cwi_analytics_choice_v1', JSON.stringify(value)), saved);
    const page = await context.newPage();
    await page.goto(url, {waitUntil:'load'});
    return {context,page,requests};
  }
  const commands = page => page.evaluate(() => (window.dataLayer || []).filter(x => x && x[0]).map(x => Array.from(x)));
  const events = async page => (await commands(page)).filter(x => x[0] === 'event');
  try {
    const f = await fixture('https://www.cochinwood.in/contact?email=private@example.test&q=secret#private');
    check(f.requests.length === 1, 'No Google request before consent');
    check(await f.page.locator('#cwi-privacy').isVisible(), 'Consent choices visible');
    await f.page.getByRole('button', {name:'Essential only', exact:true}).click();
    check(f.requests.length === 1, 'Denial makes no Google request');
    await f.page.getByRole('button', {name:'Analytics choices', exact:true}).click();
    await f.page.getByRole('button', {name:'Allow analytics', exact:true}).click();
    await f.page.waitForFunction(() => document.querySelector('script[src*="gtm.js"]'));
    check(f.requests.filter(r => r.url === GOOGLE).length === 1, 'Only configured GTM loader is requested once');
    check(f.requests.every(r => r.method === 'GET'), 'No network mutations');
    await f.page.evaluate(() => {
      cwiAnalytics.track('form_view', '/contact');
      cwiAnalytics.track('form_view', '/contact');
      cwiAnalytics.track('quote_click', '/contact?email=private@example.test');
      cwiAnalytics.track('unknown_private_event', '/contact');
    });
    check(await f.page.evaluate(() => { const q = window.dataLayer; const ready = q.findIndex(x => x.event === 'cwi_analytics_ready'); const view = q.findIndex(x => x[0] === 'event' && x[1] === 'page_view'); return ready >= 0 && ready < view; }), 'Container initialization event precedes manual page_view');
    let sent = await events(f.page);
    check(sent.filter(x => x[1] === 'page_view').length === 1, 'One page_view per page');
    check(sent.filter(x => x[1] === 'quote_form_view').length === 1, 'One contact form view despite repeated first-party view signals');
    check(sent.every(x => x[2].send_to === 'G-QD4G3EYG2G'), 'Every analytics event targets approved GA4 ID');
    check(sent.every(x => x[2].page_location === 'https://www.cochinwood.in/contact'), 'Queries and fragments excluded from page location');
    check(!JSON.stringify(await commands(f.page)).includes('private') && !JSON.stringify(await commands(f.page)).includes('secret'), 'No query, form values or fragment data in analytics commands');
    await f.context.addCookies([{name:'_ga',value:'synthetic',domain:'.cochinwood.in',path:'/',secure:true}]);
    await f.page.getByRole('button', {name:'Analytics choices', exact:true}).click();
    await f.page.getByRole('button', {name:'Essential only', exact:true}).click();
    const count = sent.length;
    await f.page.evaluate(() => { cwiAnalytics.track('form_start','/contact'); cwiAnalytics.track('quote_click','/contact'); });
    check((await events(f.page)).length === count, 'Withdrawal blocks subsequent app analytics events');
    check(await f.page.evaluate(() => window['ga-disable-G-QD4G3EYG2G'] === true), 'Withdrawal activates GA disable flag');
    check(!(await f.context.cookies()).some(c => c.name === '_ga'), 'Withdrawal removes synthetic GA cookie');
    check(await f.page.getByRole('button', {name:'Analytics choices', exact:true}).evaluate(e => document.activeElement === e), 'Closing choices restores keyboard focus');
    await f.page.getByRole('button', {name:'Analytics choices', exact:true}).click();
    await f.page.getByRole('button', {name:'Allow analytics', exact:true}).click();
    check((await events(f.page)).filter(x => x[1] === 'page_view').length === 1, 'Reaccepting does not duplicate page_view');
    await f.context.close();
    for (const [url, saved, label] of [
      ['https://preview.cochinwood-web.pages.dev/contact', {value:'accepted',saved:Date.now()}, 'Preview'],
      ['http://127.0.0.1:8873/contact', {value:'accepted',saved:Date.now()}, 'Local preview'],
      ['https://www.cochinwood.in/contact', {value:'denied',saved:Date.now()}, 'Saved denial'],
      ['https://www.cochinwood.in/contact', {value:'accepted',saved:Date.now()-181*86400000}, 'Expired consent'],
    ]) {
      const item = await fixture(url,saved);
      check(item.requests.length === 1, label + ' makes no Google request');
      check((await events(item.page)).length === 0, label + ' queues no analytics event');
      await item.context.close();
    }
    const success = await fixture('https://www.cochinwood.in/contact?sent=1', {value:'accepted',saved:Date.now()});
    check(!(await events(success.page)).some(x => x[1] === 'quote_form_view'), 'Success page does not count as a new form view');
    await success.context.close();
    for (const [width,height] of [[320,568],[640,360],[1440,900]]) {
      const item = await fixture('https://www.cochinwood.in/contact',null,width,height);
      check(await item.page.locator('#cwi-privacy').evaluate(e => e.getBoundingClientRect().left >= 0 && e.getBoundingClientRect().right <= innerWidth), 'Privacy panel fits viewport '+width+'x'+height);
      await item.page.getByRole('button',{name:'Essential only',exact:true}).click();
      check(await item.page.locator('#cwi-privacy').isHidden(), 'Choice remains operable '+width+'x'+height);
      await item.context.close();
    }
    console.log(JSON.stringify({passed:assertions.length, assertions, limitation:'GTM is intercepted. Live container configuration, Google delivery, and third-party behavior after withdrawal require separate review.'},null,2));
  } finally { await browser.close(); }
})().catch(error => {console.error(error.stack); process.exitCode=1;});
