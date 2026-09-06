/* Meaningful browser journeys against the isolated local commerce harness.
   No production routes, payment providers, or email services are contacted. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const base = process.env.COMMERCE_PREVIEW_URL || 'http://127.0.0.1:8891';
const output = process.env.COMMERCE_PREVIEW_ARTIFACTS || path.join(__dirname,'qa');
fs.mkdirSync(output,{recursive:true});
const results = [];
const sourceHashes = () => Object.fromEntries(['index.html','staff.html','commerce.css','shop.js','staff.js','test-preview.cjs'].map(name => [name,createHash('sha256').update(fs.readFileSync(path.join(__dirname,name))).digest('hex')]));
async function check(name,fn) { await fn(); results.push({name,pass:true}); }
async function waitLoaded(page) { await page.locator('.product-card').first().waitFor(); }
async function testMode(page) { await page.getByRole('button',{name:'Test checkout',exact:true}).click(); await page.getByRole('button',{name:'Add to selection'}).first().waitFor(); }
async function add(page,family,thickness,quantity=1) {
  const card = page.locator(`[data-family="${family}"].product-card`);
  await card.getByRole('button',{name:`${thickness} mm`,exact:true}).click();
  await card.locator('[data-quantity-input=product]').fill(String(quantity));
  await card.getByRole('button',{name:'Add to selection'}).click();
}
async function create(page,quantity=1) {
  await add(page,'prem_hw_gurjan',12,quantity);
  await page.locator('#delivery-postcode').fill('683542'); await page.locator('#postcode-form button').click();
  await page.locator('#continue-checkout').click(); await page.locator('#fill-test-details').click();
  await page.locator('#details-form button[type=submit]').click(); await page.locator('#review-confirm').check();
  await page.locator('#create-order').click(); await page.locator('#payment-title').waitFor();
}
(async () => {
  const browser = await chromium.launch({headless:true,channel:'chrome'});
  const context = await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const page = await context.newPage(); const pageErrors = []; const external = [];
  page.on('pageerror',error => pageErrors.push(error.message));
  await context.route('**/*',async(route) => { const url = new URL(route.request().url()); if (!['127.0.0.1','localhost'].includes(url.hostname)) { external.push(url.href); await route.abort(); } else await route.continue(); });
  try {
    await check('Actual catalogue is blocked and variant deep links work',async() => {
      await page.goto(base + '/commerce-preview/?sku=prem_marine_gurjan_18'); await waitLoaded(page);
      assert.equal(await page.locator('[data-add]:disabled').count(),2);
      assert.equal(await page.locator('[data-select-sku="prem_marine_gurjan_18"]').getAttribute('aria-pressed'),'true');
      assert.equal(await page.locator('meta[name=robots]').getAttribute('content'),'noindex, nofollow, noarchive');
      assert.match(await page.locator('#mode-note').innerText(),/purchasing is not open/i);
      await page.screenshot({path:path.join(output,'shop-actual-desktop.png')});
    });
    await check('Multi-product basket updates, removes, and persists only SKU and quantity',async() => {
      await testMode(page); await add(page,'prem_hw_gurjan',12,2); await add(page,'prem_marine_gurjan',18,3); await add(page,'prem_hw_gurjan',18,1);
      assert.equal(await page.locator('.basket-item').count(),3);
      await page.locator('[data-remove="prem_hw_gurjan_18"]').click();
      assert.equal(await page.locator('.basket-item').count(),2);
      assert.match(await page.locator('#basket-count').innerText(),/5 sheets/);
      const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('cwi.preview.cart.test')));
      assert.deepEqual(stored,[{sku:'prem_hw_gurjan_12',quantity:2},{sku:'prem_marine_gurjan_18',quantity:3}]);
      await page.reload(); await waitLoaded(page); await testMode(page);
      assert.equal(await page.locator('.basket-item').count(),2);
    });
    await check('Unsupported and eligible PIN codes use backend totals',async() => {
      await page.locator('#delivery-postcode').fill('560001'); await page.locator('#postcode-form button').click();
      await page.waitForFunction(() => document.querySelector('#delivery-message').classList.contains('error'));
      assert.equal(await page.locator('#continue-checkout').isDisabled(),true);
      await page.locator('#delivery-postcode').fill('683542'); await page.locator('#postcode-form button').click();
      await page.waitForFunction(() => !document.querySelector('#continue-checkout').disabled);
      assert.match(await page.locator('#totals').innerText(),/640/);
      assert.match(await page.locator('#delivery-message').innerText(),/2–4 days/);
      await page.evaluate(() => window.scrollTo(0,0));
      await page.screenshot({path:path.join(output,'shop-test-desktop.png')});
    });
    await check('A delayed quote cannot overwrite a changed PIN or basket',async() => {
      let release; let entered; const received = new Promise(resolve => { entered=resolve; }); const held = new Promise(resolve => { release=resolve; });
      await page.route('**/api/commerce/quote',async(route) => { const response = await route.fetch(); entered(); await held; await route.fulfill({response}); });
      await page.locator('#postcode-form button').click(); await received;
      await page.locator('#delivery-postcode').fill('560001');
      release(); await page.waitForTimeout(150);
      assert.equal(await page.locator('#continue-checkout').isDisabled(),true);
      assert.equal(await page.locator('#totals').innerText(),'');
      await page.unroute('**/api/commerce/quote');
      await page.locator('#delivery-postcode').fill('683542'); await page.locator('#postcode-form button').click();
      await page.waitForFunction(() => !document.querySelector('#continue-checkout').disabled);
      let releaseCart; let enteredCart; const receivedCart = new Promise(resolve => { enteredCart=resolve; }); const heldCart = new Promise(resolve => { releaseCart=resolve; });
      await page.route('**/api/commerce/quote',async(route) => { const response = await route.fetch(); enteredCart(); await heldCart; await route.fulfill({response}); });
      await page.locator('#postcode-form button').click(); await receivedCart;
      await page.locator('[data-scope=basket][data-sku=prem_hw_gurjan_12][data-quantity-action=plus]').click(); releaseCart(); await page.waitForTimeout(150);
      assert.equal(await page.locator('#continue-checkout').isDisabled(),true);
      await page.unroute('**/api/commerce/quote');
      await page.locator('[data-scope=basket][data-sku=prem_hw_gurjan_12][data-quantity-action=minus]').click();
      await page.locator('#postcode-form button').click(); await page.waitForFunction(() => !document.querySelector('#continue-checkout').disabled);
      let releaseMode; let enteredMode; const receivedMode = new Promise(resolve => { enteredMode=resolve; }); const heldMode = new Promise(resolve => { releaseMode=resolve; });
      await page.route('**/api/commerce/quote',async(route) => { const response = await route.fetch(); enteredMode(); await heldMode; await route.fulfill({response}); });
      await page.locator('#postcode-form button').click(); await receivedMode;
      await page.getByRole('button',{name:'Actual setup',exact:true}).click(); await waitLoaded(page); releaseMode(); await page.waitForTimeout(150);
      assert.equal(await page.locator('#continue-checkout').isDisabled(),true);
      assert.equal(await page.locator('[data-add]:disabled').count(),2);
      await page.unroute('**/api/commerce/quote'); await testMode(page);
      await page.locator('#delivery-postcode').fill('683542'); await page.locator('#postcode-form button').click(); await page.waitForFunction(() => !document.querySelector('#continue-checkout').disabled);
    });
    await check('Accessible field validation and synthetic-only customer details',async() => {
      await page.locator('#continue-checkout').click(); await page.locator('#details-form button[type=submit]').click();
      assert.equal(await page.locator('#details-errors').isVisible(),true); assert.equal(await page.locator('#buyer-name').getAttribute('aria-invalid'),'true');
      await page.locator('#fill-test-details').click(); await page.locator('#buyer-email').fill('real@example.com'); await page.locator('#details-form button[type=submit]').click();
      assert.match(await page.locator('#buyer-email-error').innerText(),/@example.invalid/);
      await page.locator('#buyer-email').fill('preview@example.invalid');
      await page.locator('#buyer-gstin').fill('bad'); await page.locator('#details-form button[type=submit]').click(); assert.equal(await page.locator('#buyer-gstin').getAttribute('aria-invalid'),'true');
      await page.locator('#buyer-gstin').fill('32ABCDE1234F1Z5'); await page.locator('#details-form button[type=submit]').click(); await page.locator('#review-title').waitFor();
      const storage = await page.evaluate(() => JSON.stringify({...localStorage})); assert.equal(storage.includes('Preview Customer'),false); assert.equal(storage.includes('example.invalid'),false); assert.equal(storage.includes('Test Building'),false);
      await page.locator('#create-order').click(); assert.match(await page.locator('#order-error').innerText(),/Confirm/);
    });
    let paidId;
    await check('Order creation preserves the full basket and simulation recovers a lost payment response',async() => {
      await page.locator('#review-confirm').check();
      let entered; let release; const hit = new Promise(resolve => {entered=resolve;}); const held = new Promise(resolve => {release=resolve;});
      await page.route('**/api/commerce/orders',async(route) => { const response=await route.fetch(); entered(); await held; await route.fulfill({response}); });
      await page.locator('#create-order').click(); await hit; assert.equal(await page.getByRole('button',{name:'Actual setup',exact:true}).isDisabled(),true); assert.equal(await page.locator('[data-quantity-input=basket]').first().isDisabled(),true); release();
      await page.locator('#payment-title').waitFor(); await page.unroute('**/api/commerce/orders');
      paidId = await page.locator('.payment-heading p').innerText(); assert.match(paidId,/^CWI-/);
      let committed;
      await page.route('**/api/commerce/preview/payment',async(route) => { committed = await route.fetch(); await route.abort('failed'); });
      await page.getByRole('button',{name:'Simulate success'}).click();
      await page.getByRole('heading',{name:'Your test order is paid.'}).waitFor();
      assert.equal(committed.status(),200); await page.unroute('**/api/commerce/preview/payment');
      await page.screenshot({path:path.join(output,'checkout-test-paid.png'),fullPage:true});
    });
    await check('Staff owner, assigned sales, unassigned sales and Purchase scopes',async() => {
      const staff = await context.newPage(); await staff.goto(base + '/commerce-preview/staff.html?order=' + encodeURIComponent(paidId));
      await staff.locator('.order-row').first().waitFor(); assert.match(await staff.locator('#outbox-list').innerText(),/cochinwoodindia@gmail.com/); assert.match(await staff.locator('#outbox-list').innerText(),/edwin.david@cochinwood.in/); assert.match(await staff.locator('#outbox-list').innerText(),/assigned-sales@example.invalid/);
      assert.match(await staff.locator('#order-detail-content').innerText(),/32ABCDE1234F1Z5/);
      await staff.screenshot({path:path.join(output,'staff-owner-desktop.png')});
      await staff.locator('#preview-role').selectOption('sales'); await staff.waitForFunction(() => !document.querySelector('#refresh').disabled); assert.ok(await staff.locator('.order-row').count() > 0); assert.match(await staff.locator('#outbox-list').innerText(),/restricted/);
      await staff.locator('#preview-role').selectOption('unassigned_sales'); await staff.waitForFunction(() => !document.querySelector('#refresh').disabled); assert.equal(await staff.locator('.order-row').count(),0);
      await staff.locator('#preview-role').selectOption('purchase'); await staff.waitForFunction(() => !document.querySelector('#refresh').disabled); assert.equal(await staff.locator('.order-row').count(),0); assert.match(await staff.locator('#orders-list').innerText(),/does not have access/);
      await staff.close();
    });
    await check('Full test refund records a stock review, then a new order refreshes stock',async() => {
      await page.getByRole('button',{name:'Simulate full refund',exact:true}).click(); await page.getByRole('heading',{name:'Test refund recorded.'}).waitFor(); assert.match(await page.locator('.payment-status').innerText(),/stock review/);
      const response = page.waitForResponse(response => response.url().endsWith('/api/commerce/catalogue?mode=test'));
      await page.locator('#new-order').click(); await response; await waitLoaded(page); assert.equal(await page.locator('.basket-item').count(),0);
    });
    await check('Cancelled payment records a terminal test state',async() => {
      await create(page); await page.getByRole('button',{name:'Simulate cancellation',exact:true}).click(); await page.getByRole('heading',{name:'Test payment closed.'}).waitFor(); assert.match(await page.locator('.receipt-lines').innerText(),/Cancelled/);
      await page.locator('#new-order').click(); await waitLoaded(page);
    });
    await check('Shop and staff remain within viewport at 320, 390, 768, 1229 and 1440 pixels',async() => {
      for (const viewport of [{width:320,height:740},{width:390,height:844},{width:768,height:1024},{width:1229,height:584},{width:1440,height:900}]) {
        await page.setViewportSize(viewport); await page.goto(base + '/commerce-preview/'); await waitLoaded(page); await testMode(page);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth),false,`Shop overflow at ${viewport.width}`);
        const images=await page.locator('.product-image').evaluateAll(images=>images.every(image=>image.complete&&image.naturalWidth>0)); assert.equal(images,true);
        const ratios=await page.locator('.product-image').evaluateAll(images=>images.map(image=>image.getBoundingClientRect().width / image.getBoundingClientRect().height));
        assert.ok(ratios.every(ratio=>ratio>=1.29&&ratio<=1.39),`Material image aspect ratio at ${viewport.width}: ${ratios}`);
        await page.screenshot({path:path.join(output,`shop-test-${viewport.width}.png`),fullPage:true});
        await page.goto(base + '/commerce-preview/staff.html?order=' + encodeURIComponent(paidId)); await page.waitForFunction(() => !document.querySelector('#refresh').disabled);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth),false,`Staff overflow at ${viewport.width}`);
        if(viewport.width===390||viewport.width===1229) await page.screenshot({path:path.join(output,`staff-owner-${viewport.width}.png`),fullPage:true});
      }
    });
    await check('Keyboard selection and Add keep focus and update the basket',async() => {
      await page.goto(base + '/commerce-preview/'); await waitLoaded(page); await testMode(page);
      const thickness = page.locator('[data-select-sku=prem_hw_gurjan_18]'); await thickness.focus(); await page.keyboard.press('Space');
      assert.equal(await page.locator('[data-select-sku=prem_hw_gurjan_18]').getAttribute('aria-pressed'),'true');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.selectSku),'prem_hw_gurjan_18');
      const addButton = page.locator('[data-add=prem_hw_gurjan_18]'); await addButton.focus(); await page.keyboard.press('Enter');
      assert.equal(await page.locator('.basket-item').count(),1); assert.match(await page.locator('#basket-count').innerText(),/1 sheet/);
    });
    await check('No browser exceptions or external network calls',async() => { assert.deepEqual(pageErrors,[]); assert.deepEqual(external,[]); });
    fs.writeFileSync(path.join(output,'browser-proof.json'),JSON.stringify({passed:true,verified_at:new Date().toISOString(),source_sha256:sourceHashes(),checks:results,order_id:paidId,external_requests:external,browser_errors:pageErrors},null,2));
    console.log(JSON.stringify({passed:true,checks:results.length,order_id:paidId,output},null,2));
  } catch(error) { await page.screenshot({path:path.join(output,'failure.png'),fullPage:true}); fs.writeFileSync(path.join(output,'browser-proof.json'),JSON.stringify({passed:false,checks:results,error:error.stack,external_requests:external,browser_errors:pageErrors},null,2)); console.error(error); process.exitCode=1; }
  finally { await browser.close(); }
})();
