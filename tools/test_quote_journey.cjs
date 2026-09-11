// Local isolated browser only. Every non-local request is blocked; native POST is intercepted.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.CWI_TEST_ORIGIN || 'http://127.0.0.1:8873';
const receiptPath=process.argv[2];
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname)) throw Error('Local test origin required');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage(); const posts=[]; let successBeacons=0;
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function isolate(route){
  const url=new URL(route.request().url());
  if(url.pathname==='/web-lead') {posts.push(route.request().postData());return route.fulfill({status:200,contentType:'text/html',body:'<p>Local mock: the save failed. Use browser Back and retry.</p>'});}
  if(url.pathname==='/cw-event' && (route.request().postData()||'').includes('form_submit_success'))successBeacons++;
  if(['127.0.0.1','localhost'].includes(url.hostname))return route.continue();
  return route.abort();
 }
 await page.route('**/*',isolate);
 const row=i=>page.locator('#cwq-items [data-quote-item]').nth(i);
 const field=(i,key)=>row(i).locator('[data-item-field="'+key+'"]');
 async function fillItem(i,data){for(const [key,value] of Object.entries(data)){const f=field(i,key);if(key==='product'||key==='unit')await f.selectOption(value);else if(key==='help_me_choose')await f.setChecked(value);else await f.fill(value);}}
 async function token(){await page.locator('#cwq2-form').evaluate(f=>{let x=f.querySelector('[name="cf-turnstile-response"]');if(!x){x=document.createElement('input');x.type='hidden';x.name='cf-turnstile-response';f.append(x);}x.value='local-mocked-turnstile-token';});}
 async function submit(){await page.waitForTimeout(3100);await page.locator('button[type=submit]').click();await page.waitForURL('**/web-lead');return new URLSearchParams(posts.at(-1));}
 for(const width of [312,390,768,887,1100,1440]){
  await page.setViewportSize({width,height:900});await page.goto(base+'/contact');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'contact overflow '+width);
 }
 const presets={'packing-plywood':'Packing Plywood','commercial-plywood':'Commercial Plywood','okoume-plywood':'Okoume Plywood','rubberwood-plywood':'Rubberwood Plywood','film-faced-shuttering-plywood':'Film Faced/Shuttering','marine-plywood':'BWP Marine Plywood - IS 710','bwr-hardwood-plywood':'BWR Hardwood Plywood - IS 303','container-flooring-plywood':'Container Flooring','block-board-flush-doors':'Block Board/Flush Door','plywood-boxes-crates':'Wooden/Plywood Packing Case','plywood-pallets':'Plywood Pallets','sawn-timber':'Timber/Runners/Planks','chequered-anti-skid-plywood':'Chequered Anti-Skid Plywood','finger-joint-board':'Finger-Joint Board','particle-board':'Particle Board','plywood-cable-drums':'Plywood Cable Drums','premium-hardwood-plywood':'Premium Hardwood Plywood'};
 for(const [slug,value] of Object.entries(presets)){await page.goto(base+'/contact?product='+slug);assert.equal(await field(0,'product').inputValue(),value,slug);}
 await page.setViewportSize({width:390,height:844});
 await page.goto(base+'/contact?product=marine-plywood');
 await page.evaluate(()=>{sessionStorage.removeItem('cwq_draft_v2');sessionStorage.setItem('cwq_retry','legacy-v1-submitted-0001');});await page.reload();
 assert.notEqual(await page.locator('[name=enquiry_id]').inputValue(),'legacy-v1-submitted-0001','Standalone legacy retry cannot replay an older v1 enquiry');
 for(const [name,value] of Object.entries({name:'Synthetic local buyer',company:'Local fixture only',email:'buyer@example.invalid',phone:'+910000000000',destination:'Jebel Ali, UAE',description:'Keep these three products separate.\nDelivery in October.'}))await page.locator('#cwq2-form [name="'+name+'"]').fill(value);
 await page.locator('[name=incoterm]').selectOption('FOB Cochin');
 await fillItem(0,{grade:'BWP',thickness:'18 mm',dimensions:'2440 x 1220 mm',quantity:'240',unit:'Sheets'});
 await page.locator('#cwq-add-item').click();
 await fillItem(1,{product:'Timber/Runners/Planks',grade:'Kiln dried',thickness:'50 mm',dimensions:'2400 x 100 x 50 mm',quantity:'3.5',unit:'CBM'});
 await page.locator('#cwq-add-item').click();await row(2).locator('[data-remove-item]').click();
 assert.equal(await page.locator('#cwq-items [data-quote-item]').count(),2);
 assert(await field(1,'product').evaluate(el=>el===document.activeElement),'Remove moves focus to adjacent item');
 await page.locator('#cwq-add-item').click();await fillItem(2,{product:'Help me choose',quantity:'2',unit:'40ft containers'});
 assert(await page.evaluate(()=>{const ids=[...document.querySelectorAll('#cwq2-form [id]')].map(el=>el.id);return ids.length===new Set(ids).size;}),'Unique item IDs after removal/add');
 assert(await page.locator('#cwq2-form').evaluate(f=>f.checkValidity()),'Unknown specifications allowed');
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Three-item mobile layout');
 await page.waitForTimeout(3100);await page.locator('button[type=submit]').click();assert.equal(posts.length,0,'Missing verification token never posts');
 assert.match(await page.locator('#cwq2-error').innerText(),/Verification has not finished/);
 await field(1,'quantity').fill('-1');await token();await page.locator('button[type=submit]').click();assert.equal(posts.length,0,'Invalid second-item quantity blocks entire enquiry');
 await field(1,'quantity').fill('3.5');
 const first=await submit();const firstBody=posts.at(-1);const expected=JSON.parse(first.get('enquiry'));
 assert.equal(expected.version,2);assert.equal(expected.items.length,3);assert.equal(expected.items[0].quantity,'240');assert.equal(expected.items[1].quantity,'3.5');assert.equal(expected.items[1].unit,'CBM');assert.equal(expected.items[2].help_me_choose,true);assert.equal(expected.destination,'Jebel Ali, UAE');assert.equal(expected.original_text,'Keep these three products separate.\nDelivery in October.');assert.equal(first.get('spec_grade'),'18 mm BWP');
 const firstKey=first.get('enquiry_id');assert.match(firstKey,/^[\da-f-]{36}$/);
 await page.goBack();await page.waitForSelector('#cwq-items');await page.reload();
 assert.equal(await page.locator('#cwq-items [data-quote-item]').count(),3);assert.equal(await field(1,'quantity').inputValue(),'3.5');
 await page.goto(base+'/contact?sent=1');
 assert.equal(await page.locator('#cwq-items [data-quote-item]').count(),3,'Unconfirmed redirect preserves all items');assert.match(await page.locator('#cwq2-error').innerText(),/could not confirm/);
 await token();const second=await submit();assert.equal(second.get('enquiry_id'),firstKey,'Identical retry keeps the idempotency key');assert.deepEqual(JSON.parse(second.get('enquiry')),expected);
 await page.goBack();await page.waitForSelector('#cwq-items');await field(0,'quantity').fill('400');await token();const changed=await submit();assert.notEqual(changed.get('enquiry_id'),firstKey,'Changed items cannot replay an earlier enquiry');
 await page.goto(base+'/contact?sent=1&received='+changed.get('enquiry_id'));
 assert.equal(await page.locator('#cwq2-form .cw-form__ok').count(),1);assert.equal(await page.evaluate(()=>sessionStorage.getItem('cwq_draft_v2')),null,'Accepted matching response clears draft');
 await page.reload();assert.equal(successBeacons,0,'A query string never fabricates a conversion beacon');
 await page.goto(base+'/contact');
 for(const [name,value] of Object.entries({name:'Synthetic size test',company:'Local fixture only',email:'size@example.invalid',phone:'+910000000000',destination:'Kochi'}))await page.locator('#cwq2-form [name="'+name+'"]').fill(value);
 await fillItem(0,{product:'Packing Plywood',quantity:'100',unit:'Sheets'});
 for(let i=1;i<20;i++){await page.locator('#cwq-add-item').click();await fillItem(i,{product:'Packing Plywood',quantity:String(100+i),unit:'Sheets'});}
 assert(await page.locator('#cwq-add-item').isDisabled());await token();const twenty=await submit();assert.equal(JSON.parse(twenty.get('enquiry')).items.length,20);assert(Buffer.byteLength(posts.at(-1))<30000,'20 concise items fit native request budget');
 await page.goBack();await page.waitForSelector('#cwq-items');
 await page.locator('textarea[name=description]').fill('木'.repeat(4000));await token();const before=posts.length;await page.waitForTimeout(3100);await page.locator('button[type=submit]').click();
 assert.equal(posts.length,before,'Encoded byte ceiling stops oversized request');assert.match(await page.locator('#cwq2-error').innerText(),/too long/);assert.equal(await page.locator('#cwq-items [data-quote-item]').count(),20);assert.equal((await page.locator('textarea[name=description]').inputValue()).length,4000,'Oversized input remains editable');
 await page.evaluate(()=>{const draft=JSON.parse(sessionStorage.getItem('cwq_draft_v2'));draft.at=Date.now()-5*60*60*1000;sessionStorage.setItem('cwq_draft_v2',JSON.stringify(draft));});await page.reload();assert.equal(await page.locator('#cwq-items [data-quote-item]').count(),1);assert.equal(await page.locator('[name=name]').inputValue(),'');assert.equal(await page.evaluate(()=>sessionStorage.getItem('cwq_draft_v2')),null,'Expired draft is removed, not merely hidden');
 await page.evaluate(()=>sessionStorage.setItem('cwq_draft_v2',JSON.stringify({at:Date.now(),items:[null],shared:{}})));await page.reload();assert.equal(await page.locator('#cwq-items [data-quote-item]').count(),1,'Malformed saved rows cannot break the form');
 const nojs=await browser.newContext({javaScriptEnabled:false});const nativePage=await nojs.newPage();await nativePage.route('**/*',isolate);await nativePage.goto(base+'/contact');assert.equal(await nativePage.locator('#cwq-items [data-quote-item]').count(),1);assert(await nativePage.locator('#cwq-add-item').isHidden());assert.equal(await nativePage.locator('select[name=products]').count(),1);await nojs.close();
 assert.deepEqual(errors,[],'No controller runtime errors');
 if(receiptPath)fs.writeFileSync(receiptPath,JSON.stringify({at:new Date().toISOString(),scope:'Isolated local browser; native POST intercepted; no real enquiry sent',postBody:firstBody,items:expected.items.length,nativeBytes:Buffer.byteLength(firstBody),twentyItemNativeBytes:Buffer.byteLength(posts.at(-1)),layouts:[312,390,768,887,1100,1440],presets:16,checks:'independent items, help, removal/focus/IDs, verification, quantity, retry restoration/dedupe, legacy-key isolation, accepted-only clearing, expired/malformed draft clearing, 20 items, byte budget, native no-JS fallback'},null,2)+'\n');
 console.log('PASS local multi-product browser journey: 6 widths, all 16 presets, 3-item native POST, accessibility, validation, retry/confirmation semantics, 20-item budget and native fallback.');
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
