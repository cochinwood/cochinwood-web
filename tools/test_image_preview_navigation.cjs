// Local-only Hardwood and same-origin image-preview navigation checks.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const origin=process.argv[2]||'http://127.0.0.1:8899';
const shotDir=process.argv[3]||'';
assert(['127.0.0.1','localhost','[::1]'].includes(new URL(origin).hostname),'Loopback only');

(async()=>{
  const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||'chrome'});
  let checks=0;
  async function makeContext(options={}) {
    const context=await browser.newContext({serviceWorkers:'block',reducedMotion:'reduce',...options});
    await context.route('**/*',route=>{
      const request=route.request(),url=new URL(request.url());
      if(url.origin===new URL(origin).origin&&request.method()==='GET') return route.continue();
      return route.abort();
    });
    return context;
  }
  async function hardwood(page,width,height,shotName) {
    await page.setViewportSize({width,height});
    const response=await page.goto(origin+'/premium-hardwood-plywood',{waitUntil:'load'});
    assert.equal(response.status(),200);
    await page.evaluate(()=>document.fonts.ready);
    const hero=page.locator('.cw-page-hero__media img');
    assert.equal(await hero.getAttribute('alt'),'Premium Hardwood plywood');
    assert.equal(await hero.locator('xpath=ancestor::a').count(),0,'Hero must not open a raw asset');
    assert.equal(await hero.locator('xpath=ancestor::button[@data-image-preview]').count(),1,'Hero uses the in-page preview');
    await hero.evaluate(img=>img.complete&&img.naturalWidth?undefined:img.decode());
    const geometry=await hero.evaluate(img=>{
      const rect=img.parentElement.getBoundingClientRect(),style=getComputedStyle(img);
      return {fit:style.objectFit,ratio:rect.width/rect.height,naturalRatio:img.naturalWidth/img.naturalHeight,srcset:img.srcset};
    });
    assert.equal(geometry.fit,'contain');
    assert(Math.abs(geometry.ratio-4/3)<0.02,'Hero stage retains 4:3');
    assert(Math.abs(geometry.naturalRatio-4/3)<0.01,'Selected responsive hero retains 4:3');
    assert(geometry.srcset.includes('320w')&&geometry.srcset.includes('1448w'),'Responsive hero candidates');
    assert.equal(await page.locator('header .cw-hd__brand').getAttribute('href'),'/');
    assert.equal(await page.locator('#nav a',{hasText:'Products'}).getAttribute('href'),'/products');
    assert.equal(await page.locator('.cw-page-hero__button').first().getAttribute('href'),'/contact?product=premium-hardwood-plywood#quote');
    if(shotDir) await page.screenshot({path:path.join(shotDir,shotName),fullPage:true});
    checks+=11;
  }
  try {
    const desktop=await makeContext({viewport:{width:1440,height:900}}),page=await desktop.newPage();
    await hardwood(page,1440,900,'premium-hardwood-v2-desktop.png');
    const heroTrigger=page.locator('.cw-page-hero__media [data-image-preview]');
    await heroTrigger.click(); await assertVisible(page.locator('.cw-image-preview'));
    assert.equal(new URL(page.url()).pathname,'/premium-hardwood-plywood');
    assert.equal(await page.locator('header').getAttribute('aria-hidden'),'true');
    assert.equal(await page.locator('main').evaluate(e=>e.inert),true);
    await page.keyboard.press('Escape'); await assertHidden(page.locator('.cw-image-preview'));
    assert.equal(await page.locator('header').getAttribute('aria-hidden'),null);
    assert.equal(await page.locator('main').evaluate(e=>e.inert),false);
    assert.equal(await heroTrigger.evaluate(e=>document.activeElement===e),true,'Hero preview returns focus'); checks+=4;

    await heroTrigger.click(); await assertVisible(page.locator('.cw-image-preview'));
    await page.evaluate(()=>{
      document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
      document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    });
    await assertHidden(page.locator('.cw-image-preview'));
    assert.equal(new URL(page.url()).pathname,'/premium-hardwood-plywood','Repeated Escape must not leave the page');
    assert.equal(await page.evaluate(()=>Boolean(history.state&&history.state.cwImagePreview)),false); checks+=3;

    await heroTrigger.click(); await assertVisible(page.locator('.cw-image-preview'));
    await page.locator('.cw-image-preview__close').evaluate(button=>{button.click();button.click();});
    await assertHidden(page.locator('.cw-image-preview'));
    assert.equal(new URL(page.url()).pathname,'/premium-hardwood-plywood','Repeated Close must not leave the page'); checks+=2;

    await heroTrigger.click(); await assertVisible(page.locator('.cw-image-preview'));
    await page.evaluate(()=>document.querySelector('header').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})));
    await assertHidden(page.locator('.cw-image-preview'));
    assert.equal(await heroTrigger.evaluate(e=>document.activeElement===e),true,'Document Escape returns focus'); checks+=2;

    await heroTrigger.click(); await assertVisible(page.locator('.cw-image-preview'));
    await page.evaluate(()=>window.dispatchEvent(new PopStateEvent('popstate',{state:history.state})));
    assert.equal(await page.locator('main').evaluate(e=>e.inert),true);
    await page.keyboard.press('Escape'); await assertHidden(page.locator('.cw-image-preview'));
    assert.equal(await page.locator('main').evaluate(e=>e.inert),false,'Re-entry must restore original inert state');
    assert.equal(await page.locator('header').getAttribute('aria-hidden'),null,'Re-entry must restore background accessibility'); checks+=3;

    await heroTrigger.click(); await assertVisible(page.locator('.cw-image-preview'));
    await page.reload({waitUntil:'load'});
    await assertHidden(page.locator('.cw-image-preview'));
    assert.equal(await page.evaluate(()=>Boolean(history.state&&history.state.cwImagePreview)),false,'Reload clears stale preview history');
    assert.equal(await page.evaluate(()=>history.scrollRestoration),'auto','Reload restores automatic scrolling');
    assert.equal(new URL(page.url()).pathname,'/premium-hardwood-plywood'); checks+=4;

    await page.locator('.cw-page-hero__button').first().click();
    assert.equal(new URL(page.url()).pathname,'/contact');
    assert.equal(new URL(page.url()).searchParams.get('product'),'premium-hardwood-plywood');
    assert.equal(new URL(page.url()).hash,'#quote');
    await page.waitForFunction(()=>document.querySelector('[data-item-field="product"]')?.value==='Premium Hardwood Plywood');
    assert.equal(await page.locator('[data-item-field="product"]').first().inputValue(),'Premium Hardwood Plywood');
    await page.goBack({waitUntil:'load'});
    assert.equal(new URL(page.url()).pathname,'/premium-hardwood-plywood'); checks+=5;

    await page.goto(origin+'/bwr-hardwood-plywood',{waitUntil:'load'});
    const diagram=page.locator('a[href="/files/Editorial/plywood-layers.svg"]');
    await diagram.scrollIntoViewIfNeeded();
    await diagram.focus();
    await diagram.click();
    const scrollY=await page.evaluate(()=>window.scrollY);
    const dialog=page.locator('.cw-image-preview');
    await assertVisible(dialog);
    assert.equal(new URL(page.url()).pathname,'/bwr-hardwood-plywood');
    assert.equal(await page.locator('.cw-image-preview__back').textContent(),'← Back to page');
    assert.equal(await page.locator('.cw-image-preview__close').textContent(),'Close');
    assert.equal(await page.locator('.cw-image-preview__back').evaluate(e=>document.activeElement===e),true);
    await page.keyboard.press('Escape'); await assertHidden(dialog);
    assert.equal(await diagram.evaluate(e=>document.activeElement===e),true,'Escape returns focus');
    await page.waitForFunction(expected=>Math.abs(window.scrollY-expected)<3,scrollY);
    await diagram.click(); await assertVisible(dialog);
    await page.goBack(); await assertHidden(dialog);
    assert.equal(await diagram.evaluate(e=>document.activeElement===e),true,'Browser Back returns focus');
    await diagram.click(); await assertVisible(dialog);
    await page.locator('.cw-image-preview__close').click(); await assertHidden(dialog);
    const textLink=await page.evaluate(()=>{
      const anchor=document.createElement('a'); anchor.id='cw-text-image-test';
      anchor.href='/files/Editorial/plywood-layers.svg'; anchor.textContent='View full diagram';
      document.querySelector('main').append(anchor); return anchor.id;
    });
    await page.locator('#'+textLink).click(); await assertVisible(dialog);
    assert.equal(await page.locator('.cw-image-preview__stage img').getAttribute('alt'),'View full diagram');
    await page.locator('.cw-image-preview__back').click(); await assertHidden(dialog);
    checks+=15;
    await desktop.close();

    const mobile=await makeContext({viewport:{width:390,height:844},hasTouch:true}),phone=await mobile.newPage();
    await hardwood(phone,390,844,'premium-hardwood-v2-mobile.png');
    const mobileHero=phone.locator('.cw-page-hero__media [data-image-preview]');
    await mobileHero.tap(); await assertVisible(phone.locator('.cw-image-preview'));
    await phone.locator('.cw-image-preview__close').tap(); await assertHidden(phone.locator('.cw-image-preview')); checks+=3;
    const burger=phone.locator('.cw-burger');
    await burger.tap(); assert.equal(await burger.getAttribute('aria-expanded'),'true');
    assert.equal(await phone.locator('#nav').evaluate(e=>getComputedStyle(e).visibility!=='hidden'&&getComputedStyle(e).display!=='none'),true);
    await phone.keyboard.press('Escape'); assert.equal(await burger.getAttribute('aria-expanded'),'false');
    assert.equal(await burger.evaluate(e=>document.activeElement===e),true,'Mobile Escape returns focus');
    await burger.tap(); await Promise.all([
      phone.waitForURL(url=>url.pathname==='/products'),
      phone.locator('#nav a[href="/products"]').tap()
    ]);
    assert.equal(new URL(phone.url()).pathname,'/products');
    await phone.goBack({waitUntil:'load'});
    await phone.goto(origin+'/bwr-hardwood-plywood',{waitUntil:'load'});
    const mobileDiagram=phone.locator('a[href="/files/Editorial/plywood-layers.svg"]');
    await mobileDiagram.scrollIntoViewIfNeeded(); await mobileDiagram.tap();
    await assertVisible(phone.locator('.cw-image-preview'));
    assert.equal(await phone.locator('.cw-image-preview__back').isVisible(),true);
    assert.equal(await phone.locator('.cw-image-preview__close').isVisible(),true);
    await phone.locator('.cw-image-preview__back').tap(); await assertHidden(phone.locator('.cw-image-preview'));
    checks+=9;
    await mobile.close();
    console.log(JSON.stringify({result:'PASS',checks,origin,externalRequests:'blocked',forms:'not submitted',screenshots:shotDir||null}));
  } finally { await browser.close(); }
})().catch(error=>{console.error(error.stack);process.exitCode=1});

async function assertVisible(locator){await locator.waitFor({state:'visible'});assert.equal(await locator.getAttribute('aria-modal'),'true');}
async function assertHidden(locator){await locator.waitFor({state:'hidden'});}
