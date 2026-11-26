const el=id=>document.getElementById(id); let csrf='';
async function api(path,options={}) { const r=await fetch(path,options); const d=await r.json(); if(!r.ok) throw new Error(d.error||'요청 실패'); return d; }
function nonce(){const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const s=Array.from(b,x=>x.toString(16).padStart(2,'0')).join('');return `${s.slice(0,8)}-${s.slice(8,12)}-${s.slice(12,16)}-${s.slice(16,20)}-${s.slice(20)}`;}
function post(body,token){return {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token,'X-Request-Nonce':nonce(),'X-Request-Timestamp':String(Math.floor(Date.now()/1000))},body:JSON.stringify(body)};}
async function refresh(){const p=await api('/api/profile');csrf=(await api('/api/csrf')).csrf_token;el('profile').textContent=`${p.student_name} (${p.github_id})`;const list=await api('/api/memos');el('memos').replaceChildren();for(const m of list){const li=document.createElement('li');li.textContent=`[${m.author}] ${m.content}`;el('memos').append(li);}el('login').hidden=true;el('board').hidden=false;}
function run(fn){return async()=>{try{await fn();el('status').textContent='완료';}catch(e){el('status').textContent=e.message;}};}
el('signin').onclick=run(async()=>{const t=(await api('/api/login-csrf')).csrf_token;await api('/api/login',post({username:el('uid').value,password:el('pw').value},t));el('pw').value='';await refresh();});
el('save').onclick=run(async()=>{await api('/api/memos',post({content:el('content').value},csrf));el('content').value='';await refresh();});
el('logout').onclick=run(async()=>{await api('/api/logout',post({},csrf));location.reload();});refresh().catch(()=>{});
