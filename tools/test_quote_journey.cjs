// Run against a locally served dist/ only. Every non-local request is intercepted.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true, channel:'chrome'});
  const page = await browser.newPage();
  let posted;
  let successBeacons = 0;
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/web-lead') {
      posted = new URLSearchParams(route.request().postData());
      return route.fulfill({status:200, contentType:'text/html', body:'<p>Local mock accepted</p>'});
    }
    if (url.pathname === '/cw-event' && (route.request().postData() || '').includes('form_submit_success')) successBeacons++;
    if (url.hostname === '127.0.0.1') return route.continue();
    return route.abort();
  });
  for (const width of [312,390,1440]) {
    await page.setViewportSize({width,height:900});
    for (const path of ['/', '/contact.html', '/products.html']) {
      await page.goto('http://127.0.0.1:8873'+path);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Overflow ${width} ${path}`);
    }
  }
  await page.goto('http://127.0.0.1:8873/contact.html?product=okoume-plywood');
  assert(await page.locator('input[value="Okoume Plywood"]').isChecked());
  await page.locator('[name=name]').fill('Synthetic local test');
  await page.locator('[name=company]').fill('Local test only');
  await page.locator('[name=email]').fill('test@example.invalid');
  await page.locator('[name=phone]').fill('+910000000000');
  await page.locator('[name=destination]').fill('Kochi');
  await page.locator('[name=help_me_choose]').check();
  await page.locator('textarea[name=description]').fill('Help choose panels for packing.');
  assert(await page.locator('form').evaluate(f => f.checkValidity()), 'Unknown specs must be allowed');
  await page.waitForTimeout(3100);
  await page.locator('button[type=submit]').click();
  assert.equal(posted, undefined, 'Unverified form must not post');
  await page.locator('form').evaluate(f => {
    const token = document.createElement('input'); token.name='cf-turnstile-response'; token.value='local-mock-token'; f.append(token);
  });
  await page.locator('button[type=submit]').click();
  await page.waitForURL('**/web-lead');
  const enquiry = JSON.parse(posted.get('enquiry'));
  assert.equal(enquiry.version,1);
  assert.equal(enquiry.product,'Okoume Plywood');
  assert.equal(enquiry.help_me_choose,true);
  assert.equal(enquiry.grade,'');
  assert.equal(enquiry.original_text,'Help choose panels for packing.');
  assert.equal(enquiry.destination,'Kochi');
  assert.match(posted.get('enquiry_id'), /^[\da-f-]{36}$/);
  await page.goto('http://127.0.0.1:8873/contact.html?sent=1');
  await page.reload();
  assert.equal(successBeacons,0);
  await page.goto('http://127.0.0.1:8873/contact.html?product=marine-plywood');
  for (const [name,value] of Object.entries({name:'Synthetic export', company:'Local mock', email:'export@example.invalid',phone:'+910000000000',destination:'Jebel Ali',grade:'BWP',thickness:'18 mm',dimensions:'2440 x 1220 mm',quantity:'2'})) {
    await page.locator(`form [name="${name}"]`).fill(value);
  }
  await page.locator('[name=unit]').selectOption({label:'40ft containers'});
  await page.locator('[name=incoterm]').selectOption({label:'FOB Cochin'});
  await page.locator('textarea[name=description]').fill('Export requirement.');
  await page.locator('form').evaluate(f => {
    const token = document.createElement('input'); token.name='cf-turnstile-response'; token.value='local-mock-token'; f.append(token);
  });
  await page.waitForTimeout(3100);
  await page.locator('button[type=submit]').click();
  await page.waitForURL('**/web-lead');
  const exportEnquiry=JSON.parse(posted.get('enquiry'));
  assert.equal(exportEnquiry.unit,'40ft containers');
  assert.equal(exportEnquiry.quantity,'2');
  assert.equal(exportEnquiry.incoterm,'FOB Cochin');
  assert.equal(exportEnquiry.thickness,'18 mm');
  assert.equal(exportEnquiry.help_me_choose,false);
  assert.equal(posted.get('spec_grade'),'18 mm BWP');
  assert.equal(exportEnquiry.original_text,'Export requirement.');
  await page.goto('http://127.0.0.1:8873/packing-plywood.html');
  assert(await page.locator('a[href*="contact?product=packing-plywood"]').count());
  console.log('PASS: 312/390/1440 layouts, product presets, unknown specifications, verification gate, domestic/export v1 native POST, retry UUID, success reload, product CTA');
  await browser.close();
})().catch(err => {console.error(err);process.exit(1);});

