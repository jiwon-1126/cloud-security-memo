'use strict';
const el = id => document.getElementById(id);
let csrf = '', busy = false, authenticated = false;
function notice(message, error = false) {
  el('status').textContent = message;
  el('status').classList.toggle('error', error);
  el('status').hidden = !message;
}
function showLogin(message = '', error = false) {
  authenticated = false; csrf = '';
  el('loading').hidden = true; el('board').hidden = true;
  el('login').hidden = false;
  el('profile-name').textContent = ''; el('profile-github').textContent = '';
  el('memos').replaceChildren(); el('content').value = ''; el('pw').value = '';
  counter(); notice(message, error);
}
async function api(path, options = {}) {
  const response = await fetch(path, {...options, credentials: 'same-origin', cache: 'no-store'});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `요청 실패 (${response.status})`);
    error.status = response.status;
    if (response.status === 401 && path !== '/api/login') showLogin('로그인이 필요합니다. 다시 로그인해 주세요.', true);
    throw error;
  }
  return data;
}
function nonce() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const s = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
  return `${s.slice(0,8)}-${s.slice(8,12)}-${s.slice(12,16)}-${s.slice(16,20)}-${s.slice(20)}`;
}
function post(body, token) {
  return {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':token,'X-Request-Nonce':nonce(),'X-Request-Timestamp':String(Math.floor(Date.now()/1000))},body:JSON.stringify(body)};
}
function renderMemos(list) {
  el('memos').replaceChildren(); el('count').textContent = String(list.length); el('empty').hidden = list.length > 0;
  for (const m of list) {
    const li = document.createElement('li'); li.className = 'memo';
    const meta = document.createElement('div'); meta.className = 'memo-meta';
    const author = document.createElement('strong'); author.textContent = m.author;
    const time = document.createElement('time'); time.textContent = m.created_at || '작성 시간 없음';
    const content = document.createElement('p'); content.className = 'memo-body'; content.textContent = m.content;
    meta.append(author, time); li.append(meta, content); el('memos').append(li);
  }
}
async function refresh() {
  const profile = await api('/api/profile');
  const token = await api('/api/csrf');
  const list = await api('/api/memos');
  csrf = token.csrf_token;
  el('profile-name').textContent = profile.student_name;
  el('profile-github').textContent = `GitHub: ${profile.github_id}`;
  renderMemos(list); authenticated = true;
  el('loading').hidden = true; el('login').hidden = true; el('board').hidden = false;
}
function counter() { el('counter').textContent = `${el('content').value.length} / 2000`; }
function run(fn) {
  return async event => {
    event.preventDefault(); if (busy) return; busy = true;
    for (const button of document.querySelectorAll('button')) button.disabled = true;
    try { await fn(); }
    catch (error) { if (error.status !== 401 || authenticated || !el('login').hidden) notice(error.message || '요청 실패', true); }
    finally { busy = false; for (const button of document.querySelectorAll('button')) button.disabled = false; }
  };
}
el('login-form').addEventListener('submit', run(async () => {
  const token = await api('/api/login-csrf');
  await api('/api/login', post({username:el('uid').value,password:el('pw').value},token.csrf_token));
  el('pw').value = ''; await refresh(); notice('로그인되었습니다.');
}));
el('memo-form').addEventListener('submit', run(async () => {
  const content = el('content').value;
  if (!content.trim()) { notice('메모 내용을 입력해 주세요.', true); return; }
  await api('/api/memos', post({content},csrf));
  el('content').value = ''; counter(); notice('메모가 등록되었습니다.');
  try { renderMemos(await api('/api/memos')); } catch (error) { if (error.status !== 401) notice('메모는 등록되었으나 목록 갱신에 실패했습니다. 새로고침해 주세요.',true); }
}));
el('refresh').addEventListener('click',run(async()=>{await refresh();notice('목록을 갱신했습니다.');}));
el('logout').addEventListener('click',run(async()=>{await api('/api/logout',post({},csrf));showLogin('로그아웃되었습니다.');}));
el('content').addEventListener('input',counter);
refresh().catch(error=>{showLogin(error.status===401?'': '서비스 연결에 실패했습니다. 서버 상태를 확인해 주세요.',error.status!==401);});
