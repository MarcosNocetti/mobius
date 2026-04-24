"""Minimal web chat UI — accessible from any device via ngrok."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["web"])

CHAT_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Mobius Chat</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#0a0a1a;color:#e0e0e0;height:100vh;display:flex;flex-direction:column}
.header{background:#1a1a2e;padding:12px 16px;text-align:center;border-bottom:1px solid #333}
.header h1{color:#00b4d8;font-size:1.2rem}
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
.status{text-align:center;color:#888;font-size:.8rem;padding:4px}
</style>
</head>
<body>

<div class="header"><h1>Mobius</h1></div>

<div id="auth">
  <h3 style="color:#00b4d8;text-align:center;margin-bottom:16px" id="auth-title">Sign In</h3>
  <input type="email" id="email" placeholder="Email">
  <input type="password" id="password" placeholder="Password">
  <button onclick="auth()">Sign In</button>
  <div class="toggle" onclick="toggleAuth()">Don't have an account? Sign Up</div>
  <div id="auth-error" style="color:#f87171;text-align:center;margin-top:8px"></div>
</div>

<div id="chat" style="display:none;flex:1;flex-direction:column">
  <div class="messages" id="messages"></div>
  <div class="typing" id="typing" style="display:none">Mobius está pensando...</div>
  <div class="input-bar">
    <input type="text" id="input" placeholder="Ask Mobius..." onkeydown="if(event.key==='Enter')send()">
    <button id="send-btn" onclick="send()">Send</button>
  </div>
</div>

<script>
const BASE = window.location.origin;
let token = null;
let ws = null;
let isSignUp = false;

function toggleAuth() {
  isSignUp = !isSignUp;
  document.getElementById('auth-title').textContent = isSignUp ? 'Sign Up' : 'Sign In';
  document.querySelector('#auth button').textContent = isSignUp ? 'Sign Up' : 'Sign In';
  document.querySelector('#auth .toggle').textContent = isSignUp
    ? 'Already have an account? Sign In'
    : "Don't have an account? Sign Up";
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
    document.getElementById('chat').style.display = 'flex';
    connectWS();
  } catch(e) { errEl.textContent = e.message; }
}

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/chat?token=${token}`);
  ws.onmessage = (e) => {
    const d = JSON.parse(e.data);
    if (d.type === 'token') {
      appendToken(d.content);
    } else if (d.type === 'error') {
      appendMsg('error', d.content);
      document.getElementById('typing').style.display = 'none';
      document.getElementById('send-btn').disabled = false;
    } else if (d.type === 'done') {
      finalizeMsg();
      document.getElementById('typing').style.display = 'none';
      document.getElementById('send-btn').disabled = false;
    }
  };
  ws.onclose = () => setTimeout(connectWS, 2000);
}

let currentAssistant = null;
function appendMsg(role, text) {
  const el = document.createElement('div');
  el.className = 'msg ' + role;
  el.textContent = text;
  document.getElementById('messages').appendChild(el);
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
  ws.send(JSON.stringify({message: text, model: 'gemini-flash'}));
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def web_chat():
    return HTMLResponse(content=CHAT_HTML)
