// Local-only headless layout regression audit. NODE_PATH may point at bundled Playwright.
// Usage: node tools/test_responsive_layout.cjs [http://127.0.0.1:8873] [report.json]
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const origin=process.argv[2]||'http://127.0.0.1:8873';
assert(['127.0.0.1','localhost','[::1]'].includes(new URL(origin).hostname),'Loopback only');
const dist=path.resolve(__dirname,'../dist');
const pages=['sitemap-cms.xml','sitemap-post.xml'].flatMap(n=>[...fs.readFileSync(path.join(dist,n),'utf8').matchAll(/<loc>(.*?)<\/loc>/g)].map(m=>new URL(m[1]).pathname));
const templates=['/','/products','/contact','/about','/industries','/resources','/packing-plywood','/marine-plywood','/plywood-factory','/company-verification','/woods-we-use','/woods-we-use/teak','/blogs','/export','/export/uae'];
const widths=(process.env.CWI_LAYOUT_WIDTHS||'320,390,620,768,860,861,900,1024,1440,1920').split(',').map(Number);
assert(widths.every(w=>Number.isInteger(w)&&w>=280&&w<=3840),'Valid viewport widths required');
const tasks=[];for(const width of widths)for(const url of ([320,1024].includes(width)?pages:templates.filter(p=>pages.includes(p))))tasks.push({width,url});
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||'chrome'});
 const failures=[],blocked=new Set();let count=0;
 async function worker(){
  const context=await browser.newContext({serviceWorkers:'block'});
  await context.route('**/*',r=>{const u=new URL(r.request().url());if(u.origin===new URL(origin).origin&&r.request().method()==='GET')return r.continue();blocked.add(u.hostname);return r.abort()});
  const page=await context.newPage();
  while(tasks.length){const task=tasks.shift();try{
   await page.setViewportSize({width:task.width,height:900});
   const response=await page.goto(origin+task.url,{waitUntil:'load',timeout:20000});
   assert(response.status()===200,'HTTP '+response.status());
   await page.evaluate(()=>document.fonts.ready);
   const result=await page.evaluate(()=>{
    const width=innerWidth, bad=[];
    const selector=el=>el.tagName.toLowerCase()+(el.id?'#'+el.id:'')+(el.classList.length?'.'+[...el.classList].slice(0,3).join('.'):'');
    const visible=el=>{const s=getComputedStyle(el);return s.display!=='none'&&s.visibility!=='hidden'&&el.getClientRects().length};
    function clipped(el){for(let a=el.parentElement;a&&a!==document.body;a=a.parentElement){const s=getComputedStyle(a);if(/auto|scroll/.test(s.overflowX))return true;if(el.tagName==='IMG'&&/hidden|clip/.test(s.overflowX))return true}return false}
    for(const el of document.querySelectorAll('header a,main h1,main h2,main h3,main p,main img,footer a,footer p')){
     if(!visible(el)||clipped(el))continue;
     const r=el.getBoundingClientRect();if(r.width&& (r.left < -1 || r.right > width+1))bad.push({selector:selector(el),left:Math.round(r.left),right:Math.round(r.right)});
    }
    const nav=document.querySelector('.cw-nav'),brand=document.querySelector('.cw-hd__brand');
    if(nav&&brand&&visible(nav)&&getComputedStyle(nav).position!=='fixed'){
     const n=nav.getBoundingClientRect(),b=brand.getBoundingClientRect();if(n.left<b.right-1)bad.push({selector:'header navigation overlaps brand'});
    }
    const broken=[...document.querySelectorAll('main img')].filter(i=>i.loading!=='lazy'&&i.complete&&!i.naturalWidth).map(selector);
    return {overflow:document.documentElement.scrollWidth>width+1,scrollWidth:document.documentElement.scrollWidth,bounds:bad.slice(0,8),broken};
   });
   if(result.overflow||result.bounds.length||result.broken.length)failures.push({...task,...result});
  }catch(e){failures.push({...task,error:String(e.message).slice(0,180)})}count++;if(count%100===0)console.log('checked',count)}await context.close();
 }
 await Promise.all(Array.from({length:4},worker));await browser.close();
 const report={checks:count,pages:pages.length,widths,blockedNonlocal:[...blocked],failures};
 if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2));
 console.log(JSON.stringify(report));process.exitCode=failures.length?1:0;
})().catch(e=>{console.error(e.message);process.exitCode=1});
