"""
Self-service setup wizard — user opens /setup in browser, follows 3 steps,
and gets Google Calendar/Gmail connected without touching the terminal.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.config import settings
from app.core.redis import redis_client

router = APIRouter(tags=["setup"])


def _render(template: str, **kwargs) -> str:
    """Replace $$KEY$$ placeholders — avoids conflicts with CSS braces."""
    for k, v in kwargs.items():
        template = template.replace(f"$${k}$$", str(v))
    return template


SETUP_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mobius — Setup</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a1a; color: #e0e0e0; min-height: 100vh; padding: 2rem; }
    .container { max-width: 700px; margin: 0 auto; }
    h1 { color: #00b4d8; font-size: 2rem; margin-bottom: 0.5rem; }
    .subtitle { color: #888; margin-bottom: 2rem; }
    .step { background: #1a1a2e; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; border-left: 4px solid #333; }
    .step.active { border-left-color: #00b4d8; }
    .step.done { border-left-color: #4ade80; }
    .step-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
    .step-num { background: #333; color: #fff; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; }
    .step.done .step-num { background: #4ade80; color: #000; }
    .step.active .step-num { background: #00b4d8; color: #000; }
    h3 { font-size: 1.1rem; }
    p, li { line-height: 1.6; color: #bbb; }
    ol { padding-left: 1.5rem; margin: 0.75rem 0; }
    a { color: #00b4d8; }
    code { background: #2a2a3e; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
    input[type=text] { width: 100%; padding: 10px 14px; border: 1px solid #333; border-radius: 8px; background: #0a0a1a; color: #e0e0e0; font-size: 0.95rem; margin-top: 0.5rem; }
    input:focus { outline: none; border-color: #00b4d8; }
    button, .btn { display: inline-block; padding: 10px 24px; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; text-decoration: none; font-weight: 600; }
    .btn-primary { background: #00b4d8; color: #000; }
    .btn-primary:hover { background: #0090b0; }
    .status { padding: 8px 16px; border-radius: 8px; margin-top: 1rem; font-size: 0.9rem; }
    .status-ok { background: #1a3a2a; color: #4ade80; }
    .redirect-uri { background: #2a2a3e; padding: 10px 14px; border-radius: 8px; font-family: monospace; font-size: 0.85rem; word-break: break-all; margin: 0.5rem 0; user-select: all; }
    label { font-size: 0.9rem; color: #999; margin-top: 0.75rem; display: block; }
    .mt { margin-top: 1rem; }
  </style>
</head>
<body>
  <div class="container">
    <h1>⚡ Mobius Setup</h1>
    <p class="subtitle">Configure suas integrações em 3 passos. Sem terminal.</p>

    <div class="step $$step1_class$$">
      <div class="step-header"><div class="step-num">1</div><h3>Criar credenciais no Google Cloud</h3></div>
      <ol>
        <li>Abra <a href="https://console.cloud.google.com/apis/credentials" target="_blank">Google Cloud → Credentials</a></li>
        <li>Crie um projeto se não tiver</li>
        <li>Configure o <a href="https://console.cloud.google.com/apis/credentials/consent" target="_blank">OAuth Consent Screen</a>: External → App name "Mobius" → Salvar</li>
        <li>Credentials → <b>+ CREATE CREDENTIALS → OAuth Client ID</b> → Web application</li>
        <li>Em "Authorized redirect URIs" adicione:<div class="redirect-uri">$$redirect_uri$$</div></li>
        <li>Copie o Client ID e Secret</li>
      </ol>
      <p class="mt">Habilite: <a href="https://console.cloud.google.com/apis/library/calendar-json.googleapis.com" target="_blank">Calendar API</a> · <a href="https://console.cloud.google.com/apis/library/gmail.googleapis.com" target="_blank">Gmail API</a></p>
    </div>

    <div class="step $$step2_class$$">
      <div class="step-header"><div class="step-num">2</div><h3>Colar credenciais aqui</h3></div>
      <form method="POST" action="/setup/save-google">
        <label for="client_id">Google Client ID</label>
        <input type="text" id="client_id" name="client_id" placeholder="xxxxx.apps.googleusercontent.com" value="$$current_client_id$$">
        <label for="client_secret">Google Client Secret</label>
        <input type="text" id="client_secret" name="client_secret" placeholder="GOCSPX-xxxxx" value="$$current_client_secret$$">
        <div class="mt"><button type="submit" class="btn btn-primary">💾 Salvar</button></div>
      </form>
      $$step2_status$$
    </div>

    <div class="step $$step3_class$$">
      <div class="step-header"><div class="step-num">3</div><h3>Conectar sua conta Google</h3></div>
      <p>Clique abaixo para autorizar o Mobius a acessar seu Calendar e Gmail.</p>
      <div class="mt">$$step3_button$$</div>
      $$step3_status$$
    </div>

    <div class="step" style="border-left-color: #00b4d8;">
      <div class="step-header"><div class="step-num">✓</div><h3>Status</h3></div>
      <p>Servidor: <code>$$server_url$$</code></p>
      <p>Google OAuth: <b>$$google_status$$</b></p>
      <p class="mt" style="color: #888; font-size: 0.85rem;">Depois de conectar, use o chat: <i>"Cria um evento na agenda amanhã às 10h"</i></p>
    </div>
  </div>
</body>
</html>"""


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/integrations/google/callback"

    has_creds = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)

    google_connected = False
    try:
        keys = await redis_client.keys("oauth:google:*")
        if keys:
            google_connected = True
    except Exception:
        pass

    step1_class = "done" if has_creds else "active"
    step2_class = "done" if has_creds else ""
    step3_class = "done" if google_connected else ("active" if has_creds else "")

    step2_status = '<div class="status status-ok">✓ Credenciais salvas</div>' if has_creds else ""

    if has_creds:
        step3_button = f'<a href="{base_url}/setup/connect-google" class="btn btn-primary">🔗 Conectar Google Calendar</a>'
    else:
        step3_button = '<button class="btn btn-primary" disabled>Salve as credenciais primeiro</button>'

    step3_status = '<div class="status status-ok">✓ Google conectado! Pode usar o chat.</div>' if google_connected else ""

    google_status = "✅ Conectado" if google_connected else ("⚙️ Credenciais OK" if has_creds else "❌ Não configurado")

    html = _render(
        SETUP_HTML,
        redirect_uri=redirect_uri,
        current_client_id=settings.GOOGLE_CLIENT_ID or "",
        current_client_secret=settings.GOOGLE_CLIENT_SECRET or "",
        step1_class=step1_class,
        step2_class=step2_class,
        step2_status=step2_status,
        step3_class=step3_class,
        step3_button=step3_button,
        step3_status=step3_status,
        server_url=base_url,
        google_status=google_status,
    )
    return HTMLResponse(content=html)


@router.post("/setup/save-google")
async def save_google_creds(request: Request):
    form = await request.form()
    client_id = form.get("client_id", "").strip()
    client_secret = form.get("client_secret", "").strip()

    if client_id and client_secret:
        await redis_client.set("setup:google_client_id", client_id)
        await redis_client.set("setup:google_client_secret", client_secret)
        settings.GOOGLE_CLIENT_ID = client_id
        settings.GOOGLE_CLIENT_SECRET = client_secret

    return RedirectResponse(url="/setup", status_code=303)


@router.get("/setup/connect-google")
async def connect_google(request: Request):
    base_url = str(request.base_url).rstrip("/")

    if not settings.GOOGLE_CLIENT_ID:
        cid = await redis_client.get("setup:google_client_id")
        csec = await redis_client.get("setup:google_client_secret")
        if cid and csec:
            settings.GOOGLE_CLIENT_ID = cid
            settings.GOOGLE_CLIENT_SECRET = csec

    if not settings.GOOGLE_CLIENT_ID:
        return HTMLResponse("❌ Configure as credenciais Google primeiro em /setup", status_code=400)

    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

    if not user:
        return HTMLResponse("❌ Nenhum usuário registrado. Faça Sign Up no app primeiro.", status_code=400)

    user_id = user.id
    await redis_client.set("setup:default_user_id", str(user_id))

    scopes = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.send"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{base_url}/integrations/google/callback",
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user_id),
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=url)
