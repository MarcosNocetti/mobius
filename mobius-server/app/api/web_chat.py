"""Web chat UI with conversation history sidebar — accessible from any device."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["web"])

CHAT_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Mobius</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#0a0a1a;color:#e0e0e0;height:100vh;display:flex;flex-direction:column}
.layout{display:flex;flex:1;overflow:hidden}
.sidebar{width:260px;background:#111122;border-right:1px solid #222;display:flex;flex-direction:column;transition:transform .2s}
.sidebar.hidden{transform:translateX(-260px);width:0;border:0}
.sidebar-header{padding:12px;border-bottom:1px solid #222;display:flex;justify-content:space-between;align-items:center}
.sidebar-header h2{color:#00b4d8;font-size:1rem}
.new-chat-btn{background:#00b4d8;color:#000;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;font-weight:600;font-size:.85rem}
.conv-list{flex:1;overflow-y:auto;padding:4px}
.conv-item{padding:10px 12px;border-radius:8px;cursor:pointer;margin:2px 0;font-size:.85rem;color:#bbb;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.conv-item:hover{background:#1a1a2e}
.conv-item.active{background:#1a1a3e;color:#00b4d8;border-left:3px solid #00b4d8}
.conv-item .date{font-size:.7rem;color:#666;display:block}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.header{background:#1a1a2e;padding:10px 16px;display:flex;align-items:center;gap:12px;border-bottom:1px solid #333}
.header h1{color:#00b4d8;font-size:1.1rem;flex:1}
.menu-btn{background:none;border:none;color:#888;font-size:1.4rem;cursor:pointer;padding:4px 8px}
.messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}
.msg{max-width:85%;padding:10px 14px;border-radius:12px;font-size:.95rem;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}
.msg.user{align-self:flex-end;background:#00b4d8;color:#000;border-bottom-right-radius:4px}
.msg.assistant{align-self:flex-start;background:#1a1a2e;border:1px solid #333;border-bottom-left-radius:4px}
.msg.error{background:#3a1a1a;border-color:#f87171;color:#f87171}
.input-bar{display:flex;padding:12px;gap:8px;background:#1a1a2e;border-top:1px solid #333}
.input-bar input{flex:1;padding:10px 14px;border:1px solid #333;border-radius:20px;background:#0a0a1a;color:#e0e0e0;font-size:1rem;outline:none}
.input-bar input:focus{border-color:#00b4d8}
.input-bar button{padding:10px 18px;border:none;border-radius:20px;background:#00b4d8;color:#000;font-weight:600;cursor:pointer;font-size:1rem}
.input-bar button:disabled{opacity:.5;cursor:not-allowed}
.typing{color:#888;font-style:italic;padding:4px 14px}
#auth{padding:24px;max-width:400px;margin:auto}
#auth input{width:100%;padding:10px;margin:8px 0;border:1px solid #333;border-radius:8px;background:#0a0a1a;color:#e0e0e0}
#auth button{width:100%;padding:12px;margin:8px 0;border:none;border-radius:8px;background:#00b4d8;color:#000;font-weight:600;cursor:pointer;font-size:1rem}
#auth .toggle{color:#00b4d8;cursor:pointer;text-align:center;margin-top:12px}
.empty-state{flex:1;display:flex;align-items:center;justify-content:center;color:#555;font-size:1.1rem}
@media(max-width:600px){.sidebar{position:fixed;z-index:10;height:100%;width:260px}.sidebar.hidden{transform:translateX(-260px)}}
</style>
</head>
<body>

<div id="auth">
  <h3 style="color:#00b4d8;text-align:center;margin-bottom:16px" id="auth-title">Sign In</h3>
  <input type="email" id="email" placeholder="Email">
  <input type="password" id="password" placeholder="Password">
  <button onclick="auth()">Sign In</button>
  <div class="toggle" onclick="toggleAuth()">Don't have an account? Sign Up</div>
  <div id="auth-error" style="color:#f87171;text-align:center;margin-top:8px"></div>
</div>

<div class="layout" id="app" style="display:none">
  <div class="sidebar" id="sidebar">
    <div class="sidebar-header">
      <h2>Conversas</h2>
      <button class="new-chat-btn" onclick="newChat()">+ Nova</button>
    </div>
    <div class="conv-list" id="conv-list"></div>
  </div>
  <div class="main">
    <div class="header">
      <button class="menu-btn" onclick="toggleSidebar()">☰</button>
      <h1 id="conv-title">Mobius</h1>
    </div>
    <div class="messages" id="messages">
      <div class="empty-state">Comece uma conversa</div>
    </div>
    <div class="typing" id="typing" style="display:none">Mobius está pensando...</div>
    <div class="input-bar">
      <input type="text" id="input" placeholder="Ask Mobius..." onkeydown="if(event.key==='Enter')send()">
      <button id="send-btn" onclick="send()">Send</button>
    </div>
  </div>
</div>

<script>
const BASE = window.location.origin;
let token = null;
let ws = null;
let isSignUp = false;
let activeConvId = null;
let conversations = [];

function toggleAuth() {
  isSignUp = !isSignUp;
  document.getElementById('auth-title').textContent = isSignUp ? 'Sign Up' : 'Sign In';
  document.querySelector('#auth button').textContent = isSignUp ? 'Sign Up' : 'Sign In';
  document.querySelector('#auth .toggle').textContent = isSignUp
    ? 'Already have an account? Sign In' : "Don't have an account? Sign Up";
}

async function auth() {
  const email = document.getElementById('email').value;
  const pass = document.getElementById('password').value;
  const errEl = document.getElementById('auth-error');
  errEl.textContent = '';
  try {
    if (isSignUp) {
      await fetch(BASE+'/auth/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email,password:pass})});
    }
    const r = await fetch(BASE+'/auth/token', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email,password:pass})});
    if (!r.ok) throw new Error('Invalid credentials');
    const d = await r.json();
    token = d.access_token;
    document.getElementById('auth').style.display = 'none';
    document.getElementById('app').style.display = 'flex';
    connectWS();
    loadConversations();
  } catch(e) { errEl.textContent = e.message; }
}

async function loadConversations() {
  const r = await fetch(BASE+'/conversations', {headers:{'Authorization':'Bearer '+token}});
  conversations = await r.json();
  renderConvList();
}

function renderConvList() {
  const el = document.getElementById('conv-list');
  el.innerHTML = '';
  for (const c of conversations) {
    const div = document.createElement('div');
    div.className = 'conv-item' + (c.id === activeConvId ? ' active' : '');
    const d = new Date(c.updated_at || c.created_at);
    div.innerHTML = `${c.title}<span class="date">${d.toLocaleDateString()} · ${c.message_count} msgs</span>`;
    div.onclick = () => loadConversation(c.id);
    el.appendChild(div);
  }
}

async function loadConversation(convId) {
  activeConvId = convId;
  renderConvList();
  const r = await fetch(BASE+'/conversations/'+convId, {headers:{'Authorization':'Bearer '+token}});
  const data = await r.json();
  document.getElementById('conv-title').textContent = data.title;
  const msgsEl = document.getElementById('messages');
  msgsEl.innerHTML = '';
  for (const m of data.messages) {
    if (m.role === 'user' || m.role === 'assistant') {
      appendMsg(m.role, m.content);
    }
  }
}

function newChat() {
  activeConvId = null;
  document.getElementById('conv-title').textContent = 'Mobius';
  document.getElementById('messages').innerHTML = '<div class="empty-state">Comece uma conversa</div>';
  renderConvList();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('hidden');
}

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/chat?token=${token}`);
  ws.onmessage = (e) => {
    const d = JSON.parse(e.data);
    if (d.type === 'conversation_id') {
      activeConvId = d.content;
      loadConversations();
    } else if (d.type === 'token') {
      appendToken(d.content);
    } else if (d.type === 'error') {
      appendMsg('error', d.content);
      finish();
    } else if (d.type === 'done') {
      finalizeMsg();
      finish();
    }
  };
  ws.onclose = () => setTimeout(connectWS, 2000);
}

function finish() {
  document.getElementById('typing').style.display = 'none';
  document.getElementById('send-btn').disabled = false;
}

let currentAssistant = null;
function appendMsg(role, text) {
  const msgsEl = document.getElementById('messages');
  // Remove empty state
  const empty = msgsEl.querySelector('.empty-state');
  if (empty) empty.remove();
  const el = document.createElement('div');
  el.className = 'msg ' + role;
  el.textContent = text;
  msgsEl.appendChild(el);
  el.scrollIntoView({behavior:'smooth'});
  return el;
}
function appendToken(text) {
  if (!currentAssistant) currentAssistant = appendMsg('assistant', '');
  currentAssistant.textContent += text;
  currentAssistant.scrollIntoView({behavior:'smooth'});
}
function finalizeMsg() { currentAssistant = null; }

function send() {
  const input = document.getElementById('input');
  const text = input.value.trim();
  if (!text || !ws) return;
  input.value = '';
  appendMsg('user', text);
  document.getElementById('typing').style.display = 'block';
  document.getElementById('send-btn').disabled = true;
  const payload = {message: text, model: 'gemini-flash'};
  if (activeConvId) payload.conversation_id = activeConvId;
  ws.send(JSON.stringify(payload));
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def web_chat():
    return HTMLResponse(content=CHAT_HTML)
