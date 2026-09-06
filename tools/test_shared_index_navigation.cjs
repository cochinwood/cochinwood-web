// Shared Home/catalogue/blog navigation regression; isolated local Chrome only.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const base=process.argv[2]||'http://127.0.0.1:8873';
assert(['127.0.0.1','localhost'].includes(new URL(base).hostname));
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 let checks=0;
 async function context(js=true){
  const c=await browser.newContext({javaScriptEnabled:js,serviceWorkers:'block',reducedMotion:'reduce'});
  await c.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin&&r.request().method()==='GET'?r.continue():r.abort());
  return c;
 }
 try{
  const c=await context(),p=await c.newPage();
  for(const width of [390,768,887,1440]){
   let reference;
   for(const route of ['/export','/industries','/','/products','/blogs']){
    await p.setViewportSize({width,height:900});
    await p.goto(base+route,{waitUntil:'load'});await p.evaluate(()=>document.fonts.ready);
    assert.equal(await p.locator('.cw-section-bar').count(),1,route+' one bar');
    const data=await p.evaluate(()=>{const b=document.querySelector('.cw-section-bar'),a=b.querySelector('.cw-section-links a'),s=getComputedStyle(a),m=b.querySelector('details');return {height:b.getBoundingClientRect().height,font:s.fontFamily,fontSize:s.fontSize,lineHeight:s.lineHeight,padding:s.padding,color:getComputedStyle(b).backgroundColor,open:m.open,overflow:document.documentElement.scrollWidth>innerWidth}});
    assert(!data.overflow,route+' overflow');assert.equal(data.open,width>760);
    if(!reference)reference=data;else for(const key of ['height','font','fontSize','lineHeight','padding','color'])assert.equal(data[key],reference[key],route+' shared '+key+' at '+width);
    checks++;
   }
  }
  await p.setViewportSize({width:390,height:844});
  await p.goto(base+'/products',{waitUntil:'load'});
  assert.equal(await p.locator('.cw-catalogue-jumps').count(),0,'No duplicate catalogue menu');
  assert.equal(await p.locator('.cw-section-links a').count(),3);
  await p.locator('.cw-section-menu summary').click();
  await p.locator('.cw-section-links a[href="#timber"]').click();
  assert.equal(new URL(p.url()).hash,'#timber');
  assert.equal(await p.locator('.cw-section-menu').evaluate(e=>e.open),false);
  await p.waitForTimeout(100);
  assert(await p.locator('#timber').evaluate(e=>e.getBoundingClientRect().top>=document.querySelector('.cw-section-bar').getBoundingClientRect().bottom-2),'Timber below sticky bar');checks++;
  await p.goto(base+'/blogs',{waitUntil:'load'});
  assert.equal(await p.locator('.cw-blog-topics').count(),1);
  assert(await p.locator('.cw-blog-location-card').count()>100,'Location directory retained');
  assert.equal(await p.locator('.cw-blog-location-card img').count(),0,'No repeated city-guide images');
  assert(await p.locator('.cw-blog-card-image img').count()>0,'Other editorial thumbnails retained');
  assert.equal(await p.locator('.cw-blog-browse .cw-blog-topics').count(),0,'No duplicate sidebar');
  await p.locator('.cw-section-menu summary').click();
  const topic=p.locator('[data-blog-topic-filter]').nth(1),key=await topic.getAttribute('data-blog-topic-filter');
  await topic.click();
  assert.equal(new URL(p.url()).searchParams.get('topic'),key);
  assert.equal(await p.locator('.cw-section-menu').evaluate(e=>e.open),false);
  await p.locator('#cw-blogsearch').fill('plywood');
  await p.waitForFunction(()=>new URL(location.href).searchParams.get('q')==='plywood');
  assert.equal(new URL(p.url()).searchParams.get('q'),'plywood');
  await p.reload({waitUntil:'load'});assert.equal(await p.locator('#cw-blogsearch').inputValue(),'plywood');
  assert.equal(await p.locator('[data-blog-topic-filter="'+key+'"]').getAttribute('aria-current'),'true');
  await p.locator('#cw-blogclear').click();
  assert.equal(new URL(p.url()).searchParams.get('topic'),null);assert.equal(new URL(p.url()).searchParams.get('q'),null);checks++;
  await c.close();
  const plain=await context(false),q=await plain.newPage();
  for(const route of ['/','/products','/blogs']){
   await q.goto(base+route,{waitUntil:'load'});
   assert(await q.locator('.cw-section-menu').evaluate(e=>e.open));
   const broken=await q.locator('.cw-section-links a').evaluateAll(links=>links.filter(a=>!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.hash));
   assert.deepEqual(broken,[],route+' native targets');checks++;
  }
  await plain.close();console.log(JSON.stringify({checks,result:'PASS',externalRequests:'blocked',forms:'not submitted'}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack);process.exitCode=1});
