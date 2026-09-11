const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../assets/cw-events.js'), 'utf8');
function run({path='/contact', search='', origin='/packing-plywood', storageFails=false}={}) {
  const events=[], listeners={};
  const form={addEventListener:(name, fn)=>{listeners[name]=fn;}};
  const ctx={location:{pathname:path,search}, document:{querySelector:()=>form,addEventListener:()=>{}},
    sessionStorage:{getItem:()=>{if(storageFails)throw Error('disabled');return origin;}},
    navigator:{sendBeacon:url=>events.push(new URL(url,'https://www.cochinwood.in'))}};
  vm.runInNewContext(source,ctx);
  return {events,listeners};
}
let r=run();
assert.deepEqual(r.events.map(x=>x.searchParams.get('n')),['form_view']);
for(let i=0;i<3;i++) {r.listeners.input({target:{value:'PRIVATE'}});r.listeners.change({});r.listeners.invalid({target:{validationMessage:'PRIVATE'}});}
assert.deepEqual(r.events.map(x=>x.searchParams.get('n')),['form_view','form_start','form_validation_error']);
for(const e of r.events) {assert.equal(e.searchParams.get('p'),'/packing-plywood');assert.deepEqual([...e.searchParams.keys()],['n','p']);assert.ok(!e.href.includes('PRIVATE'));}
assert.equal(run({search:'?sent=1'}).events.length,0,'success URL does not create a funnel visit');
assert.equal(run({search:'?sent=1&x=2'}).events.length,0);
assert.equal(run({path:'/products'}).events.length,0);
assert.equal(run({storageFails:true}).events[0].searchParams.get('p'),'/contact');
for(const origin of ['//external.invalid','/contact?email=private','https://external.invalid']) assert.equal(run({origin}).events[0].searchParams.get('p'),'/contact');
assert.equal(run({path:'/contact.html'}).events.length,1,'local extension and clean path behave alike');
assert.equal(run().events.length,1,'a reload is another view, deliberately not a unique person');
console.log('PASS form counters: once per kind/load, success suppression, source attribution and field privacy');
