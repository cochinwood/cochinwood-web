/* Isolated browser + real SQLite recovery proof. All customer inputs are synthetic;
   external network is blocked. No production/staging/checkout activation occurs. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict'),path=require('node:path'),os=require('node:os'),fs=require('node:fs');
const {pathToFileURL}=require('node:url'),{createHash}=require('node:crypto');
const appRoot=process.env.CWI_COMMERCE_APP_ROOT||path.join(os.homedir(),'cochin-wood-document-studio');
const output=process.env.COMMERCE_PREVIEW_ARTIFACTS||path.join(__dirname,'qa');
const key='cwi.preview.order-recovery.v1',passphrase='A private recovery phrase 2026!';
const checks=[],errors=[],external=[];let context,page;
async function review(page,url){
  await page.goto(url);await page.locator('.product-card').first().waitFor();await page.getByRole('button',{name:'Test checkout',exact:true}).click();
  await page.locator('[data-add=prem_hw_gurjan_12]').click();await page.locator('#delivery-postcode').fill('683542');await page.locator('#postcode-form button').click();
  await page.locator('#continue-checkout').click();await page.locator('#fill-test-details').click();await page.locator('#details-form button[type=submit]').click();await page.locator('#review-confirm').check();
}
async function optIn(page){await page.locator('.recovery-choice').evaluate(el=>el.open=true);await page.locator('#save-recovery').check();await page.locator('#recovery-passphrase').fill(passphrase);await page.locator('#recovery-passphrase-confirm').fill(passphrase);}
async function unlock(page,password=passphrase){await page.locator('#saved-recovery details').evaluate(el=>el.open=true);await page.locator('#unlock-recovery-passphrase').fill(password);await page.locator('#unlock-recovery-form button').click();}
const noPlain=value=>{for(const secret of ['Preview Customer','preview@example.invalid','Test Building','9000000000',passphrase,'access_token','expected_catalogue_fingerprint'])assert(!value.includes(secret),'browser storage contains '+secret);};
(async()=>{
  const {startPreviewServer}=await import(pathToFileURL(path.join(appRoot,'tools/commerce/preview-server.mjs')).href);
  const server=await startPreviewServer({webRoot:path.resolve(__dirname,'..'),dbPath:':memory:',port:0});
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  const count=()=>server.env.DB.raw.prepare('SELECT COUNT(*) n FROM commerce_orders').get().n;
  async function fresh(storageState,viewport={width:1229,height:800}){if(context)await context.close();context=await browser.newContext({storageState,viewport,reducedMotion:'reduce'});await context.route('**/*',route=>{if(new URL(route.request().url()).hostname!=='127.0.0.1'){external.push(route.request().url());return route.abort();}return route.continue();});page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));return page;}
  try{
    await fresh();await review(page,server.url);assert.equal(await page.locator('#save-recovery').isChecked(),false);await page.locator('#create-order').click();await page.locator('#payment-title').waitFor();
    const normal=await page.evaluate(()=>JSON.stringify({...localStorage}));noPlain(normal);assert.equal(await page.evaluate(k=>localStorage.getItem(k),key),null);
    checks.push({name:'Normal checkout requires no passphrase and stores no contact/address/token recovery',pass:true});
    await fresh();await review(page,server.url);await page.locator('#edit-details').click();await page.locator('#buyer-gstin').fill('32ABCDE1234F1Z5');await page.locator('#details-form button[type=submit]').click();await page.locator('#review-confirm').check();const originalReview=await page.locator('#review-content').innerText();await optIn(page);fs.mkdirSync(output,{recursive:true});await page.locator('.recovery-choice').screenshot({path:path.join(output,'customer-recovery-choice.png')});const writes=[];let first=true;
    await page.route('**/api/commerce/orders',async route=>{writes.push({key:route.request().headers()['idempotency-key'],body:route.request().postData()});const response=await route.fetch();if(first){first=false;assert.equal(response.status(),201);return route.abort('failed');}return route.fulfill({response});});
    await page.locator('#create-order').click();await page.waitForFunction(()=>!document.querySelector('#order-error').hidden);assert.equal(count(),2);
    const pendingState=await context.storageState();noPlain(JSON.stringify(pendingState));assert(await page.evaluate(k=>!!JSON.parse(localStorage.getItem(k)).ciphertext,key));
    assert.equal(await page.locator('#recovery-passphrase').inputValue(),'');
    await fresh(pendingState);const restoredWrites=[];page.on('request',req=>{if(req.method()==='POST' && new URL(req.url()).pathname==='/api/commerce/orders')restoredWrites.push({key:req.headers()['idempotency-key'],body:req.postData()});});
    await page.goto(server.url);await page.locator('.product-card').first().waitFor();assert.equal(restoredWrites.length,0);await unlock(page,'A wrong recovery phrase!');await page.locator('#saved-recovery-error').waitFor();assert.match(await page.locator('#saved-recovery-error').innerText(),/incorrect|damaged/);assert.equal(restoredWrites.length,0);
    await page.route('**/api/commerce/catalogue?mode=test',async route=>{const response=await route.fetch(),data=await response.json();data.products=data.products.filter(x=>x.sku!=='prem_hw_gurjan_12').map(x=>({...x,unit_price_paise:990000,name:'Changed current catalogue'}));return route.fulfill({response,json:data});});
    await unlock(page);await page.locator('#review-title').waitFor();assert.equal(restoredWrites.length,0);assert.equal(await page.locator('#review-confirm').isChecked(),false);assert.equal(await page.locator('#edit-details').isDisabled(),true);
    assert.match(await page.locator('#review-content').innerText(),/12 mm/);assert.equal((await page.locator('#review-content').innerText()).includes('Changed current catalogue'),false);assert.equal(await page.locator('.basket-item').count(),1,'an unavailable current SKU still renders the original saved item');
    assert.equal(await page.locator('#review-content').innerText(),originalReview,'recovered review retains original GSTIN, delivery window and every displayed fact');
    await page.locator('#review-confirm').check();await page.locator('#create-order').click();await page.locator('#payment-title').waitFor();assert.equal(count(),2);assert.deepEqual(restoredWrites,[writes[0]]);
    noPlain(JSON.stringify(await context.storageState()));
    checks.push({name:'Wrong passphrase sends nothing; page-close recovery preserves original facts despite current SKU removal and replays the exact request once',pass:true});
    const acceptedState=await context.storageState();await fresh(acceptedState);const calls=[];page.on('request',req=>{if(new URL(req.url()).pathname.startsWith('/api/commerce/orders'))calls.push([req.method(),new URL(req.url()).pathname]);});
    await page.goto(server.url);await page.locator('.product-card').first().waitFor();assert.deepEqual(calls,[]);await unlock(page);await page.locator('#payment-title').waitFor();assert.equal(calls.length,1);assert.equal(calls[0][0],'GET');assert.equal(count(),2);
    await page.setViewportSize({width:390,height:844});await page.locator('#saved-recovery').scrollIntoViewIfNeeded();fs.mkdirSync(output,{recursive:true});await page.screenshot({path:path.join(output,'customer-recovery-mobile.png')});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    checks.push({name:'Accepted-order recovery uses bearer status GET only, with no order/payment POST and no mobile overflow',pass:true});
    await page.locator('#forget-recovery').click();assert(await page.evaluate(k=>localStorage.getItem(k)!==null,key));assert.match(await page.locator('#forget-recovery-review').innerText(),/does not cancel/);await page.locator('#confirm-forget-recovery').click();assert.equal(await page.evaluate(k=>localStorage.getItem(k),key),null);assert.equal(count(),2);
    checks.push({name:'Forgetting requires review, clears only this device copy and preserves the server order',pass:true});
    const expiry=structuredClone(acceptedState);const item=expiry.origins[0].localStorage.find(x=>x.name===key),envelope=JSON.parse(item.value);envelope.created_at=Date.now()-25*3600000;envelope.expires_at=envelope.created_at+24*3600000;item.value=JSON.stringify(envelope);
    await fresh(expiry);let expiryPosts=0;page.on('request',r=>{if(r.method()==='POST')expiryPosts++;});await page.goto(server.url);await page.locator('.product-card').first().waitFor();assert.equal(await page.evaluate(k=>localStorage.getItem(k),key),null);assert.match(await page.locator('#saved-recovery-note').innerText(),/expired|does not cancel/);assert.equal(expiryPosts,0);
    checks.push({name:'Expired copies are removed on reopening with an existing-order warning and no automatic request',pass:true});
    const corrupt=structuredClone(acceptedState);corrupt.origins[0].localStorage.find(x=>x.name===key).value='{bad-json';await fresh(corrupt);let corruptPosts=0;page.on('request',r=>{if(r.method()==='POST')corruptPosts++;});await page.goto(server.url);await page.locator('.product-card').first().waitFor();assert.match(await page.locator('#saved-recovery-note').innerText(),/damaged/);assert.equal(await page.locator('#unlock-recovery-form').isVisible(),false);assert.equal(corruptPosts,0);
    checks.push({name:'Corrupt storage fails closed without a request or exposure of saved content',pass:true});
    await fresh();await page.addInitScript(()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='cwi.preview.order-recovery.v1')throw new DOMException('Synthetic blocked storage','QuotaExceededError');return original.call(this,k,v);};});await review(page,server.url);await optIn(page);const previous=count();await page.locator('#create-order').click();await page.locator('#order-error').waitFor();assert.equal(count(),previous);assert.match(await page.locator('#order-error').innerText(),/could not save/);await page.locator('#save-recovery').uncheck();await page.locator('#create-order').click();await page.locator('#payment-title').waitFor();assert.equal(count(),previous+1);
    checks.push({name:'Unavailable opt-in storage prevents an unsaved submission, while opting out still permits normal checkout',pass:true});
    // Ciphertext alterations cannot bypass authentication or extend the authenticated lifetime.
    await fresh(acceptedState);await page.goto(server.url);await page.locator('.product-card').first().waitFor();await page.evaluate(k=>{const e=JSON.parse(localStorage.getItem(k));e.created_at+=1000;e.expires_at+=1000;localStorage.setItem(k,JSON.stringify(e));},key);await unlock(page);await page.locator('#saved-recovery-error').waitFor();assert.match(await page.locator('#saved-recovery-error').innerText(),/incorrect|damaged/);
    checks.push({name:'Authenticated metadata rejects tampering with the saved lifetime',pass:true});
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    const hashes=Object.fromEntries(['recovery.js','shop.js','index.html','commerce.css','test-device-recovery.cjs'].map(name=>[name,createHash('sha256').update(fs.readFileSync(path.join(__dirname,name))).digest('hex')]));
    fs.writeFileSync(path.join(output,'customer-device-recovery-proof.json'),JSON.stringify({passed:true,verified_at:new Date().toISOString(),scope:'Local commerce preview, isolated SQLite and headless Chrome only',checks,source_sha256:hashes,browser_errors:errors,external_requests:external,real_data_writes:0},null,2));console.log(JSON.stringify({passed:true,checks:checks.length,errors,external},null,2));
  }catch(error){console.error(error);process.exitCode=1;}finally{await browser.close();await server.close();}
})();
