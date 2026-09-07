'use strict';
/* Opt-in device recovery. Plaintext, passphrases and CryptoKeys never enter storage.
   This vault does not establish an account, cancel an order or extend a reservation. */
window.CWIOrderRecovery = (() => {
  const STORAGE='cwi.preview.order-recovery.v1',HOURS=24*60*60*1000,ITERATIONS=600000;
  const encoder=new TextEncoder(),decoder=new TextDecoder();
  const bytes=value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));
  const base64=value=>btoa(String.fromCharCode(...new Uint8Array(value)));
  const fail=message=>{throw new Error(message);};
  function remove(){try{localStorage.removeItem(STORAGE);if(localStorage.getItem(STORAGE)!==null)throw Error();}catch{fail('This browser could not remove its saved copy. Clear this site’s browser data to remove it.');}}
  function read() {
    let raw;try{raw=localStorage.getItem(STORAGE);}catch{return {state:'unavailable'};}
    if(!raw)return {state:'empty'};
    let envelope;
    try {
      if(raw.length>160000)throw Error();envelope=JSON.parse(raw);
      const e=envelope;
      if(e.v!==1 || !Number.isSafeInteger(e.created_at) || !Number.isSafeInteger(e.expires_at) || e.expires_at-e.created_at!==HOURS || e.created_at>Date.now()+60000 || typeof e.ciphertext!=='string' || e.ciphertext.length>150000 || bytes(e.salt).length!==16 || bytes(e.iv).length!==12 || bytes(e.ciphertext).length<16)throw Error();
    }catch{return {state:'corrupt'};}
    if(Date.now()>=envelope.expires_at){try{remove();}catch{return {state:'expired',removal_failed:true};}return {state:'expired'};}
    return {state:'saved',envelope};
  }
  const aad=e=>encoder.encode(JSON.stringify([STORAGE,location.origin,e.created_at,e.expires_at]));
  async function derive(passphrase,salt) {
    if(!crypto?.subtle)fail('Encrypted recovery is unavailable in this browser. You can continue without saving.');
    if(typeof passphrase!=='string' || passphrase.length<12 || passphrase.length>256)fail('Use a passphrase of 12–256 characters. Keep it somewhere safe; it cannot be recovered.');
    const material=await crypto.subtle.importKey('raw',encoder.encode(passphrase),'PBKDF2',false,['deriveKey']);
    return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:ITERATIONS,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
  }
  function validate(payload) {
    if(!payload || payload.v!==1 || !['attempt','accepted'].includes(payload.kind))throw Error('invalid payload');
    if(payload.kind==='accepted') {
      if(!/^CWI-T-[A-Za-z0-9_-]{5,70}$/.test(payload.order_id || '') || !/^[a-f0-9]{64}$/.test(payload.access_token || ''))throw Error('invalid receipt');
    } else {
      if(!/^[A-Za-z0-9_-]{16,100}$/.test(payload.attempt?.key || '') || typeof payload.attempt?.body!=='string' || new TextEncoder().encode(payload.attempt.body).length>32768)throw Error('invalid attempt');
      const body=JSON.parse(payload.attempt.body);
      if(body.mode!=='test' || !/^[a-f0-9]{64}$/.test(body.expected_catalogue_fingerprint || '') || !Array.isArray(body.items) || !body.items.length || body.items.length>20 || body.items.some(x=>!x || !/^[a-z0-9_]{3,70}$/.test(x.sku || '') || !Number.isInteger(x.quantity) || x.quantity<1 || x.quantity>10000) || !body.buyer || !body.address || body.address.postcode!==body.postcode || !payload.quote || !Array.isArray(payload.quote.items) || payload.quote.catalogue_fingerprint!==body.expected_catalogue_fingerprint)throw Error('invalid facts');
    }
    return payload;
  }
  async function write(context,payload) {
    validate(payload);
    if(Date.now()>=context.expires_at)fail('The 24-hour recovery period has ended. The order may still exist; check its status before placing another.');
    const e={v:1,created_at:context.created_at,expires_at:context.expires_at,salt:context.salt,iv:base64(crypto.getRandomValues(new Uint8Array(12)))};
    const plain=encoder.encode(JSON.stringify(payload));if(plain.length>100000)fail('The recovery copy is too large to save.');
    e.ciphertext=base64(await crypto.subtle.encrypt({name:'AES-GCM',iv:bytes(e.iv),additionalData:aad(e)},context.key,plain));
    const raw=JSON.stringify(e);
    if(!navigator.locks?.request)fail('This browser cannot safely coordinate saved recovery between tabs. Continue without saving.');
    await navigator.locks.request(STORAGE,()=>{
      const current=read();
      if((context.persisted && (current.state!=='saved' || current.envelope.salt!==context.salt)) || (!context.persisted && current.state!=='empty'))fail('The saved copy changed in another tab. It was not overwritten. Review recovery before continuing.');
      try{localStorage.setItem(STORAGE,raw);if(localStorage.getItem(STORAGE)!==raw)throw Error();}catch{fail('This browser could not save encrypted recovery. Try again, or turn off saving to continue in this tab.');}
      context.persisted=true;
    });
    return context;
  }
  async function create(passphrase,payload) {
    const current=read();
    if(current.state==='unavailable')fail('This browser cannot access saved recovery. You can turn off saving and continue in this tab.');
    if(current.state!=='empty')fail('A recovery copy already exists here. Unlock it or explicitly forget it before saving a different order.');
    const salt=crypto.getRandomValues(new Uint8Array(16)),created_at=Date.now();
    const context={key:await derive(passphrase,salt),salt:base64(salt),created_at,expires_at:created_at+HOURS};
    return write(context,payload);
  }
  async function unlock(passphrase) {
    const current=read();if(current.state!=='saved')fail('There is no readable, unexpired recovery copy. The order may still exist; check with the team before placing another.');
    const e=current.envelope,key=await derive(passphrase,bytes(e.salt));
    let payload;try{payload=validate(JSON.parse(decoder.decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:bytes(e.iv),additionalData:aad(e)},key,bytes(e.ciphertext)))));}catch{fail('The passphrase is incorrect or the saved copy is damaged. Nothing was submitted.');}
    if(Date.now()>=e.expires_at)fail('This recovery copy has expired. The order may still exist.');
    return {payload,context:{key,salt:e.salt,created_at:e.created_at,expires_at:e.expires_at,persisted:true}};
  }
  return Object.freeze({read,create,write,unlock,remove});
})();
