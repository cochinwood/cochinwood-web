// Read-only local navigation and short-desktop hero regression checks.
// Usage: node tools/test_page_navigation.cjs [http://127.0.0.1:8873] [report.json]
// Uses installed Chrome via bundled Playwright. No external or non-GET requests.
'use strict';
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const origin = new URL(process.argv[2] || 'http://127.0.0.1:8873');
assert(['localhost','127.0.0.1','[::1]'].includes(origin.hostname), 'Loopback origin required');
assert(origin.pathname === '/' && !origin.username && !origin.password, 'Bare loopback origin required');
const NAV_ROUTES = ['/industries','/export','/export/uae','/marine-plywood','/woods-we-use/teak','/resources','/supply-markets'];
const HERO_ROUTES = ['/','/products','/industries','/export','/blogs','/woods-we-use','/about','/contact'];
const VIEWPORTS = [{width:1229,height:584,dpr:1.5625},{width:1366,height:650,dpr:1},{width:1536,height:729,dpr:1}];
const failures = [], metrics = [], blocked = new Set();
let checks = 0;

(async () => {
  const browser = await chromium.launch({headless:true,channel:'chrome'});
  async function context(options={}) {
    const c = await browser.newContext({serviceWorkers:'block',reducedMotion:'reduce',acceptDownloads:false,...options});
    // Avoid an optional banner covering the subject being measured. The privacy
    // controls have their own tests; no Google code loads on a loopback origin.
    if (options.javaScriptEnabled !== false) await c.addInitScript(() => {
      localStorage.setItem('cwi_analytics_choice_v1',JSON.stringify({value:'denied',saved:Date.now()}));
    });
    await c.route('**/*',r => {
      const u = new URL(r.request().url());
      if(u.origin === origin.origin && r.request().method() === 'GET') return r.continue();
      blocked.add(r.request().method()+' '+u.origin); return r.abort('blockedbyclient');
    });
    return c;
  }
  async function visit(page,route) {
    const response=await page.goto(new URL(route,origin).href,{waitUntil:'load',timeout:25000});
    if(response) assert.equal(response.status(),200,'Page responds200');
    else assert.equal(new URL(page.url()).pathname,new URL(route,origin).pathname,'Same-document anchor navigation');
    await page.evaluate(() => document.fonts.ready);
  }
  async function run(label,fn) {
    checks++;
    try { const result=await fn(); if(result) metrics.push({check:label,...result}); }
    catch(error) { failures.push({check:label,error:error.message}); }
  }
  async function bounds(page) {
    return page.evaluate(() => {
      const visible=e => e.getClientRects().length && getComputedStyle(e).visibility!=='hidden' && getComputedStyle(e).display!=='none';
      const bad=[];
      for(const e of document.querySelectorAll('main h1,main h2,main p,.cw-section-bar a,.cw-section-bar summary')) {
        if(!visible(e))continue;
        // An intentional scrolling menu can contain links outside its scrollport.
        let scrollport=false;
        for(let a=e.parentElement;a&&a!==document.body;a=a.parentElement) if(/auto|scroll/.test(getComputedStyle(a).overflowX))scrollport=true;
        if(scrollport)continue;
        const b=e.getBoundingClientRect();
        if(b.left < -1 || b.right > innerWidth+1) bad.push({text:e.textContent.trim().slice(0,80),left:b.left,right:b.right});
      }
      return {overflow:document.documentElement.scrollWidth>innerWidth+1,scrollWidth:document.documentElement.scrollWidth,bad};
    });
  }
  async function targetPosition(page,href) {
    return page.evaluate(href => {
      const target=document.getElementById(decodeURIComponent(href.slice(1)));
      if(!target)return null;
      const h=document.querySelector('.cw-hd').getBoundingClientRect();
      const bar=document.querySelector('.cw-section-bar');
      const b=bar?.getBoundingClientRect();
      const sticky=bar && getComputedStyle(bar).position==='sticky' && b.top<=h.bottom+3;
      const t=target.getBoundingClientRect();
      return {top:t.top,bottom:t.bottom,headerBottom:h.bottom,barTop:b?.top,barBottom:b?.bottom,occlusionBottom:sticky?Math.max(h.bottom,b.bottom):h.bottom};
    },href);
  }
  for(const width of [390,768,1229,1536]) {
    const c=await context({viewport:{width,height:width===1229?584:800}}), page=await c.newPage();
    for(const route of NAV_ROUTES) await run(`navigation ${route} ${width}`,async()=>{
      await visit(page,route);
      const bar=page.locator('.cw-section-bar');
      assert.equal(await bar.count(),1,'One consolidated section navigation bar');
      assert.equal(await page.locator('.cw-regional-navigation').evaluateAll(xs=>xs.filter(e=>!e.closest('.cw-page-navigation')).length),0,'No separate regional strip outside the compact context navigation');
      const links=bar.locator('.cw-section-links a[href^="#"]');
      const items=await links.evaluateAll(xs=>xs.map(a=>({href:a.getAttribute('href'),text:a.textContent.trim()})));
      assert(items.length>=2,'Useful section destinations present');
      const missing=await page.evaluate(items=>items.filter(a=>!document.getElementById(decodeURIComponent(a.href.slice(1)))),items);
      assert.deepEqual(missing,[],'Every section destination exists');
      assert.equal(new Set(items.map(x=>x.href)).size,items.length,'No duplicate section destinations');
      const menu=bar.locator('details').filter({has:page.locator('.cw-section-links')}).first();
      if(width>760) {
        assert(await links.first().isVisible(),'Desktop section links visible without opening a generic box');
        const scroll=bar.locator('nav[aria-label="On this page"]');
        if(await scroll.evaluate(e=>e.scrollWidth>e.clientWidth+2)) {
          const next=bar.getByRole('button',{name:'More sections',exact:true});
          assert(await next.isVisible(),'Overflowed desktop sections expose an accessible forward control');
          await next.click();
          assert(await scroll.evaluate(e=>e.scrollLeft>0),'Forward control reveals more section links');
          await scroll.evaluate(e=>{e.scrollLeft=0;});
        }
      } else {
        const summary=menu.locator('summary').first();
        if(!(await links.first().isVisible())) await summary.click();
        assert(await links.first().isVisible(),'Mobile menu opens');
        await links.first().focus(); await page.keyboard.press('Escape');
        assert(!(await menu.evaluate(e=>e.open)),'Escape closes mobile section menu');
        assert(await summary.evaluate(e=>document.activeElement===e),'Escape returns focus to menu summary');
        await summary.click();
      }
      const item=items[Math.min(1,items.length-1)];
      await links.filter({hasText:item.text}).first().click();
      await page.waitForFunction(h=>location.hash===h,item.href);
      await page.waitForFunction(h=>{
        const t=document.getElementById(decodeURIComponent(h.slice(1)));
        return t && t.getBoundingClientRect().top>=document.querySelector('.cw-hd').getBoundingClientRect().bottom-2;
      },item.href,{timeout:3500});
      const pos=await targetPosition(page,item.href);
      assert(pos.top>=pos.occlusionBottom-2,`Target hidden under header/bar: ${JSON.stringify(pos)}`);
      await page.waitForFunction(h=>[...document.querySelectorAll('.cw-section-links a')].some(a=>a.getAttribute('href')===h&&a.getAttribute('aria-current')==='location'),item.href,{timeout:3500});
      assert(pos.top< (width===1229?584:800)-30,'Selected heading is in viewport');
      const layout=await bounds(page); assert(!layout.overflow && !layout.bad.length,JSON.stringify(layout));
      // A copied URL must work without requiring a preceding menu click.
      await page.goto('about:blank');
      await visit(page,route+item.href);
      await page.waitForFunction(h=>{
        const t=document.getElementById(decodeURIComponent(h.slice(1)));
        return t && t.getBoundingClientRect().top>=document.querySelector('.cw-hd').getBoundingClientRect().bottom-2;
      },item.href,{timeout:3500});
      const initial=await targetPosition(page,item.href);
      assert(initial.top>=initial.occlusionBottom-2,`Initial hash hidden: ${JSON.stringify(initial)}`);
      return {route,width,sections:items.length,clickedTarget:pos,initialHash:initial};
    });
    await c.close();
  }
  // Native anchors and disclosures must remain usable if JavaScript is absent.
  for(const width of [390,1229]) {
    const c=await context({javaScriptEnabled:false,viewport:{width,height:800}}), page=await c.newPage();
    for(const route of ['/industries','/export/uae','/woods-we-use/teak']) await run(`no JS ${route} ${width}`,async()=>{
      await visit(page,route);
      const bar=page.locator('.cw-section-bar'), links=bar.locator('.cw-section-links a');
      if(!(await links.first().isVisible())) await bar.locator('details summary').first().click();
      assert(await links.first().isVisible(),'Native sections remain available');
      const href=await links.nth(1).getAttribute('href'); await links.nth(1).click();
      assert.equal(new URL(page.url()).hash,href,'Native anchor navigates without JS');
      const pos=await targetPosition(page,href);
      assert(pos.top>=pos.headerBottom-2,`No-JS target hidden by header: ${JSON.stringify(pos)}`);
      const layout=await bounds(page);assert(!layout.overflow && !layout.bad.length,JSON.stringify(layout));
      return {route,width,target:pos};
    });
    await c.close();
  }
  const c=await context({viewport:{width:1229,height:584}}),page=await c.newPage();
  await run('species context destinations preserved',async()=>{
    await visit(page,'/woods-we-use/teak');
    const links=await page.locator('.cw-page-navigation a').evaluateAll(xs=>xs.map(a=>({href:a.getAttribute('href'),text:a.textContent.trim()})));
    for(const href of ['/woods-we-use','/woods-we-use/subabul','/woods-we-use/venteak']) assert(links.some(x=>x.href===href),'Missing species context '+href);
    assert(links.some(x=>x.href.startsWith('/woods-we-use?group=')),'Species category retained');
    return {links};
  });
  await run('regional destinations remain available',async()=>{
    await visit(page,'/export/uae');
    const refs=await page.locator('.cw-page-navigation a').evaluateAll(xs=>xs.map(a=>a.getAttribute('href')));
    for(const expected of ['/supply-markets','/export']) assert(refs.includes(expected),'Missing regional parent '+expected);
    assert(refs.filter(x=>x.startsWith('/blogs/post/')).length>=5,'UAE city destinations retained');
    return {destinations:refs.filter(x=>!x.startsWith('#'))};
  });
  await c.close();
  for(const viewport of VIEWPORTS) {
    const c=await context({viewport:{width:viewport.width,height:viewport.height},deviceScaleFactor:viewport.dpr}), page=await c.newPage();
    for(const route of HERO_ROUTES) await run(`hero fits ${route} ${viewport.width}x${viewport.height}`,async()=>{
      await visit(page,route);
      const result=await page.evaluate(()=>{
        const hero=document.querySelector('main .cw-page-hero,main .cx-hero');
        if(!hero)return {missing:true};
        const h=hero.getBoundingClientRect(),header=document.querySelector('.cw-hd').getBoundingClientRect();
        const visible=[...hero.querySelectorAll('h1,p,a,img,figcaption')].filter(e=>e.getClientRects().length&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden');
        const clipped=visible.filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&(r.top<header.bottom-2||r.bottom>innerHeight+2||r.left<-1||r.right>innerWidth+1)}).map(e=>({tag:e.tagName,text:e.textContent.trim().slice(0,80),bounds:JSON.parse(JSON.stringify(e.getBoundingClientRect()))}));
        // Decorative full-bleed images intentionally extend a small amount for
        // parallax; their containing hero stage, not bitmap edges, is the limit.
        const meaningful=clipped.filter(e=>!(hero.classList.contains('cx-hero')&&e.tag==='IMG'));
        return {hero:{top:h.top,bottom:h.bottom,height:h.height},headerBottom:header.bottom,clipped:meaningful,viewport:[innerWidth,innerHeight]};
      });
      assert(!result.missing,'Hero present');
      assert(result.hero.bottom<=viewport.height+2,'Hero extends below initial viewport: '+JSON.stringify(result));
      assert.equal(result.clipped.length,0,'Hero copy/actions clipped: '+JSON.stringify(result));
      return {route,...viewport,...result};
    });
    await c.close();
  }
  // 768 CSS px models 200% reflow from a 1536px desktop window. Content may
  // naturally continue below the fold; it must not be clipped to a fixed stage.
  const reflow=await context({viewport:{width:768,height:650}}),rp=await reflow.newPage();
  for(const route of [...HERO_ROUTES,'/marine-plywood','/woods-we-use/teak']) await run(`200% reflow ${route}`,async()=>{
    await visit(rp,route);const result=await bounds(rp);
    assert(!result.overflow && !result.bad.length,JSON.stringify(result));
    const clip=await rp.evaluate(()=>{
      const hero=document.querySelector('main .cw-page-hero,main .cx-hero'); if(!hero)return [];
      return [...hero.querySelectorAll('h1,p,a')].filter(e=>{
        if(!e.getClientRects().length)return false;
        const b=e.getBoundingClientRect();
        for(let p=e.parentElement;p&&p!==hero.parentElement;p=p.parentElement){const s=getComputedStyle(p),r=p.getBoundingClientRect();if(/hidden|clip/.test(s.overflowY)&&(b.top<r.top-1||b.bottom>r.bottom+1))return true;}
        return false;
      }).map(e=>e.textContent.trim());
    });assert.deepEqual(clip,[],'Reflow text clipped');return {route,...result};
  });
  await reflow.close();await browser.close();
  const report={passed:failures.length===0,checks,metrics,failures,blockedRequests:[...blocked],scope:'Local isolated Chrome; navigation behavior, no-JS and short-desktop hero geometry. Not a network-delivery or visual-quality certification.'};
  if(process.argv[3])fs.writeFileSync(path.resolve(process.argv[3]),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,checks,failures,blockedRequests:report.blockedRequests},null,2));
  process.exitCode=failures.length?1:0;
})().catch(error=>{console.error(error.stack);process.exitCode=1});
