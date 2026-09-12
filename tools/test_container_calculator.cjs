// Run against the generated site. All external traffic and local beacons are blocked.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {calculate,containers} = require('../assets/container-calculator.js');
const baseline = {container:'40',thickness:12,density:650,payload:26.7,packing:300,clearance:100};
const calc = changes => calculate({...baseline,...changes});
assert.equal(calc({}).count,728,'40ft: four positions, each 182 sheets high');
assert.equal(calc({container:'20'}).count,364,'20ft: two positions, each 182 sheets high');
assert.equal(calc({}).weightCount,1136,'Weight ceiling must round down before applying geometry');
assert(Math.abs(calc({}).cargoMass - 17203.46112)<1e-6,'Cargo includes 300 kg packing, never container tare');
assert.equal(calc({payload:5}).count,202,'A low confirmed payload becomes the binding constraint');
assert.equal(calc({payload:5}).limit,'Cargo payload');
assert(calc({payload:5,packing:600}).count < calc({payload:5}).count,'Packing mass must consume payload');
assert(calc({clearance:250}).count < calc({}).count,'Runner and handling allowance must consume stack height');
assert.equal(calc({clearance:0}).count,764,'Zero height allowance is a valid comparison, not the default');
assert.equal(calc({packing:0}).cargoMass,calc({packing:0}).panelMass);
for (const container of ['20','40']) for (const thickness of [6,9,12,16,18,25]) {
  for (const payload of [5,20,26.7]) for (const packing of [0,300,900]) {
    const result=calc({container,thickness,payload,packing});
    assert(!result.error);
    assert(Number.isInteger(result.count) && result.count >= 0);
    assert(result.cargoMass <= payload * 1000 + 1e-6,'Never exceed the route payload');
    assert(result.count <= result.layoutCount,'Never exceed flat-stack capacity');
    assert(result.along*2440+(result.along-1)*50+100 <= containers[container].length);
    assert(result.across*1220+(result.across-1)*50+100 <= containers[container].doorWidth);
    assert(result.layers*thickness+100 <= containers[container].doorHeight);
    assert(result.volume <= (container==='20'?33.2:67.7),'Panel cube never exceeds container cube');
    const nextMass=result.cargoMass+result.sheetMass;
    assert(result.count===result.layoutCount || nextMass>payload*1000,'Round down without discarding a permitted sheet');
  }
}
for (const bad of [{payload:0},{payload:-1},{payload:29},{density:NaN},{density:0},{packing:-1},{packing:27000},{packing:500,payload:.2},{clearance:501},{thickness:0},{container:'unknown'}]) assert(calc(bad).error,'Reject invalid inputs '+JSON.stringify(bad));
console.log('PASS calculator arithmetic: geometry, weight, door, packing, rounding and invalid inputs.');
if (process.argv.includes('--unit')) process.exit(0);
const {chromium}=require('playwright');
const base=process.env.CWI_TEST_ORIGIN || 'http://127.0.0.1:8877';
if (!['localhost','127.0.0.1'].includes(new URL(base).hostname)) throw Error('Local preview required');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage();
 const errors=[]; page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/*',route=>{
   const url=new URL(route.request().url());
   if (!['localhost','127.0.0.1'].includes(url.hostname)) return route.abort();
   if(url.pathname==='/cw-event'||url.pathname==='/web-lead')return route.fulfill({status:204,body:''});
   return route.continue();
 });
 await page.goto(base+'/rubberwood-plywood-container-weight');
 const essential=page.getByRole('button',{name:'Essential only',exact:true});
 if(await essential.isVisible())await essential.click();
 const script=page.locator('script[src*="/assets/container-calculator."]');
 assert.equal(await script.count(),1,'Generated shell must load the fingerprinted controller exactly once');
 assert.match(await script.getAttribute('src'),/container-calculator\.[0-9a-f]{8}\.js$/);
 assert.equal(await page.locator('#cwi-res-sheets').innerText(),'728');
 assert.equal(await page.locator('#cwi-res-cbm').innerText(),'26.0 m³');
 assert.equal(await page.locator('#cwi-res-wt').innerText(),'17.2 t');
 assert(await page.locator('#cwi-calc-unavailable').isHidden());
 await page.getByLabel('Container',{exact:true}).selectOption('20');
 assert.equal(await page.locator('#cwi-res-sheets').innerText(),'364');
 assert.equal(await page.locator('#cwi-res-cbm').innerText(),'13.0 m³');
 await page.getByLabel('Panel thickness',{exact:true}).selectOption('18');
 assert.equal(await page.locator('#cwi-res-sheets').innerText(),'242','Changing thickness must change the result');
 await page.getByLabel('Confirmed cargo payload (tonnes)',{exact:true}).fill('5');
 assert.match(await page.locator('#cwi-res-limit').innerText(),/Cargo payload/);
 const before=Number((await page.locator('#cwi-res-sheets').innerText()).replace(/,/g,''));
 await page.getByLabel('Packing mass allowance (kg)',{exact:true}).fill('600');
 assert(Number((await page.locator('#cwi-res-sheets').innerText()).replace(/,/g,''))<before);
 await page.getByLabel('Confirmed cargo payload (tonnes)',{exact:true}).fill('');
 assert(await page.locator('#cwi-calc-results').isHidden(),'Blank input never retains a misleading estimate');
 assert(await page.locator('#cwi-calc-error').isVisible());
 assert.equal(await page.locator('#cwi-calc-payload').getAttribute('aria-invalid'),'true');
 await page.locator('#cwi-calc-payload').fill('26.7');
 await page.locator('#cwi-calc-packing').fill('300');
 await page.locator('#cwi-calc-th').selectOption('12');
 const withClearance=Number(await page.locator('#cwi-res-sheets').innerText());
 await page.locator('#cwi-calc-clearance').fill('250');
 assert(Number(await page.locator('#cwi-res-sheets').innerText())<withClearance);
 await page.locator('#cwi-calc-density').fill('800');
 assert.match(await page.locator('#cwi-res-check').innerText(),/Weight ceiling/);
 assert.equal(await page.locator('#cwi-calc-results').getAttribute('role'),'status');
 assert.equal(await page.locator('#cwi-calc-results').getAttribute('aria-live'),'polite');
 for (const control of await page.locator('#cwi-container-calculator input,#cwi-container-calculator select').all()) {
   assert(await control.evaluate(el=>el.labels.length>0),'Every input has a visible label');
 }
 for (const width of [312,375,390,768,1280]) {
   await page.setViewportSize({width,height:900});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No page overflow at '+width);
   assert(await page.locator('#cwi-container-calculator').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'No calculator overflow at '+width);
 }
 // Save review images only when the caller asks, without committing outputs to source.
 const screenshotDir=process.env.CWI_CALCULATOR_SCREENSHOTS;
 if(screenshotDir){
   fs.mkdirSync(screenshotDir,{recursive:true});
   for(const width of [375,1280]){
     await page.setViewportSize({width,height:1000});
     for(const [part,id] of [['inputs','cwi-container-calculator'],['results','cwi-calc-results']]){
       await page.locator('#'+id).evaluate(el=>window.scrollTo({top:el.getBoundingClientRect().top+window.scrollY-160,behavior:'instant'}));
       await page.screenshot({path:path.join(screenshotDir,'calculator-'+width+'-'+part+'.png')});
     }
   }
 }
 await page.locator('#cwi-calc-box').focus();await page.keyboard.press('Tab');
 assert.equal(await page.evaluate(()=>document.activeElement.id),'cwi-calc-th','Keyboard follows the labelled controls');
 assert.deepEqual(errors,[],'No page runtime errors');
 const nojs=await browser.newContext({javaScriptEnabled:false});
 const fallback=await nojs.newPage();await fallback.route('**/*',route=>['localhost','127.0.0.1'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
 await fallback.goto(base+'/rubberwood-plywood-container-weight');
 assert(await fallback.locator('#cwi-calc-unavailable').isVisible());
 assert(await fallback.locator('#cwi-calc-box').isDisabled(),'No inert enabled controls without JavaScript');
 assert(await fallback.locator('#cwi-calc-results').isHidden(),'No hard-coded output pretending to be a result');
 await nojs.close();await browser.close();
 console.log('PASS generated calculator browser: both containers, thickness, weight/packing, clearance, validation, labels, keyboard, five widths and no-JS fallback.');
})().catch(error=>{console.error(error);process.exit(1);});
