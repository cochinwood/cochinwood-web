/* Focused order-submission recovery checks. The real loopback server and SQLite
   ledger run in memory; no bank, customer, production or staging data is used. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict'),path=require('node:path'),os=require('node:os'),fs=require('node:fs');
const {pathToFileURL}=require('node:url'),{createHash}=require('node:crypto');
const appRoot=process.env.CWI_COMMERCE_APP_ROOT||path.join(os.homedir(),'cochin-wood-document-studio');
const out=process.env.COMMERCE_PREVIEW_ARTIFACTS||path.join(__dirname,'qa');
const checks=[],errors=[],external=[];
async function review(page,url){
  await page.goto(url);await page.locator('.product-card').first().waitFor();
  await page.getByRole('button',{name:'Test checkout',exact:true}).click();
  await page.locator('[data-add=prem_hw_gurjan_12]').click();
  await page.locator('#delivery-postcode').fill('683542');await page.locator('#postcode-form button').click();
  await page.locator('#continue-checkout').click();await page.locator('#fill-test-details').click();
  await page.locator('#details-form button[type=submit]').click();await page.locator('#review-confirm').check();
}
(async()=>{
  const {startPreviewServer}=await import(pathToFileURL(path.join(appRoot,'tools/commerce/preview-server.mjs')).href);
  const server=await startPreviewServer({webRoot:path.resolve(__dirname,'..'),dbPath:':memory:',port:0});
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  const context=await browser.newContext({reducedMotion:'reduce'});const page=await context.newPage();
  page.on('pageerror',error=>errors.push(error.message));
  await context.route('**/*',route=>{if(new URL(route.request().url()).hostname!=='127.0.0.1'){external.push(route.request().url());return route.abort();}return route.continue();});
  const count=()=>server.env.DB.raw.prepare('SELECT COUNT(*) n FROM commerce_orders').get().n;
  try{
    await review(page,server.url);const writes=[];let first=true;
    await page.route('**/api/commerce/orders',async route=>{writes.push({key:route.request().headers()['idempotency-key'],body:route.request().postData()});const response=await route.fetch();if(first){first=false;assert.equal(response.status(),201);return route.abort('failed');}return route.fulfill({response});});
    await page.locator('#create-order').click();await page.waitForFunction(()=>!document.querySelector('#order-error').hidden);
    assert.equal(count(),1,'the original order really committed before the response was lost');
    assert.equal(await page.locator('#edit-details').isDisabled(),true,'details must not discard an uncertain order claim');
    assert.equal(await page.getByRole('button',{name:'Actual setup',exact:true}).isDisabled(),true);
    assert.equal(await page.locator('[data-quantity-input=basket]').isDisabled(),true);
    await page.locator('#create-order').click();await page.locator('#payment-title').waitFor();
    assert.equal(count(),1,'retry must recover the same order, not reserve another');assert.equal(writes.length,2);assert.deepEqual(writes[0],writes[1]);
    assert.match(JSON.parse(writes[0].body).expected_catalogue_fingerprint,/^[a-f0-9]{64}$/,'the submitted order is bound to the catalogue shown in its reviewed quote');
    assert.equal(await page.getByRole('button',{name:'Actual setup',exact:true}).isDisabled(),false,'recovery releases mode controls');
    checks.push({name:'Committed order with lost response remains locked and recovers by identical request',pass:true});
    await page.unroute('**/api/commerce/orders');await page.locator('#new-order').click();await page.locator('.product-card').first().waitFor();
    await page.evaluate(()=>localStorage.clear());await review(page,server.url);
    await page.route('**/api/commerce/orders',route=>route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:{code:'stock_unavailable',message:'This test stock was reserved elsewhere. Review the selection.'}})}));
    await page.locator('#create-order').click();await page.waitForFunction(()=>document.querySelector('#order-error').textContent.includes('reserved elsewhere'));
    assert.equal(count(),1);assert.equal(await page.locator('#edit-details').isDisabled(),false);await page.locator('#edit-details').click();await page.locator('#checkout-title').waitFor();
    checks.push({name:'Definite stock refusal permits correcting details without another order',pass:true});
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    fs.mkdirSync(out,{recursive:true});const hashes=Object.fromEntries(['shop.js','test-recovery.cjs'].map(name=>[name,createHash('sha256').update(fs.readFileSync(path.join(__dirname,name))).digest('hex')]));
    fs.writeFileSync(path.join(out,'order-recovery-proof.json'),JSON.stringify({passed:true,verified_at:new Date().toISOString(),checks,source_sha256:hashes,browser_errors:errors,external_requests:external,real_data_writes:0},null,2));
    console.log(JSON.stringify({passed:true,checks:checks.length,errors,external},null,2));
  }catch(error){console.error(error);process.exitCode=1;}
  finally{await browser.close();await server.close();}
})();
