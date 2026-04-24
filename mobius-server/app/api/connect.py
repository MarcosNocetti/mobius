"""
Unified /connect endpoints — one set of routes for all integrations.
Replaces the old per-integration routers and app/api/setup.py.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.integrations.registry import integration_registry

router = APIRouter(prefix="/connect", tags=["connect"])


@router.get("/status")
async def all_status(user_id: str | None = None):
    """Return connection status for every registered integration."""
    integrations = integration_registry.get_all()
    if not user_id:
        return {"integrations": [
            {"name": i.name, "display_name": i.display_name, "connected": False, "auth_type": i.auth_type}
            for i in integrations.values()
        ]}
    statuses = await integration_registry.get_all_status(user_id)
    return {"integrations": statuses}


@router.get("/{integration_name}")
async def connect(request: Request, integration_name: str, user_id: str | None = None):
    """Start OAuth or show API-key instructions for a given integration."""
    try:
        integration = integration_registry.get(integration_name)
    except KeyError:
        return HTMLResponse(f"Integration '{integration_name}' not found", status_code=404)

    base_url = str(request.base_url).rstrip("/")

    if integration.auth_type == "api_key":
        return {"message": f"Configure {integration.display_name} API key in Settings"}

    if not user_id:
        from app.core.database import AsyncSessionLocal
        from app.models.user import User
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if not user:
                return HTMLResponse("No users registered. Sign up first.", status_code=400)
            user_id = str(user.id)

    url = integration.get_authorize_url(user_id, base_url)

    # Twitter PKCE: persist the verifier after generating the URL
    if hasattr(integration, "store_pkce_verifier"):
        await integration.store_pkce_verifier()

    return RedirectResponse(url=url)


@router.get("/{integration_name}/callback")
async def callback(request: Request, integration_name: str, code: str, state: str):
    """Handle OAuth callback for any integration."""
    try:
        integration = integration_registry.get(integration_name)
    except KeyError:
        return HTMLResponse(f"Integration '{integration_name}' not found", status_code=404)

    base_url = str(request.base_url).rstrip("/")
    await integration.handle_callback(code, state, base_url)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>body{{background:#0a0a1a;color:#e0e0e0;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}}
    .card{{text-align:center;background:#1a1a2e;padding:3rem;border-radius:16px;border:2px solid #4ade80}}
    h1{{color:#4ade80;font-size:2rem}}p{{color:#bbb;margin-top:1rem}}</style></head>
    <body><div class="card"><h1>{integration.display_name} conectado!</h1><p>Pode fechar esta aba e voltar ao chat.</p></div></body></html>"""
    return HTMLResponse(content=html)


# --- Legacy redirect: Google Cloud Console still points to /integrations/google/callback ---

legacy_router = APIRouter(tags=["connect-legacy"])


@legacy_router.get("/integrations/google/callback")
async def legacy_google_callback(request: Request, code: str, state: str):
    return await callback(request, "google", code, state)
