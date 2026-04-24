import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from jose import JWTError
from app.core.database import get_session
from app.core.security import decode_token
from app.models.automation import Automation

router = APIRouter(prefix="/automations", tags=["automations"])
bearer = HTTPBearer()


async def _get_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        return decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class AutomationCreate(BaseModel):
    name: str
    description: str = ""
    trigger_type: str = "cron"
    trigger_config: dict = {}
    script: str = ""


class AutomationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_config: dict | None = None
    script: str | None = None
    status: str | None = None


class AutomationResponse(BaseModel):
    id: str
    name: str
    description: str
    trigger_type: str
    trigger_config: dict
    script: str
    status: str
    last_run: datetime | None
    last_result: str | None
    last_error: str | None
    run_count: int


@router.post("", response_model=AutomationResponse, status_code=201)
async def create_automation(
    body: AutomationCreate,
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
):
    automation = Automation(
        user_id=user_id,
        name=body.name,
        description=body.description,
        trigger_type=body.trigger_type,
        trigger_config=json.dumps(body.trigger_config),
        script=body.script,
        status="draft" if not body.script else "active",
    )
    session.add(automation)
    await session.commit()
    await session.refresh(automation)
    return _to_response(automation)


@router.get("", response_model=list[AutomationResponse])
async def list_automations(
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Automation).where(Automation.user_id == user_id)
    )
    return [_to_response(a) for a in result.scalars().all()]


@router.get("/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: str,
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
):
    automation = await session.get(Automation, automation_id)
    if not automation or automation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Automation not found")
    return _to_response(automation)


@router.patch("/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: str,
    body: AutomationUpdate,
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
):
    automation = await session.get(Automation, automation_id)
    if not automation or automation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Automation not found")
    if body.name is not None:
        automation.name = body.name
    if body.description is not None:
        automation.description = body.description
    if body.trigger_config is not None:
        automation.trigger_config = json.dumps(body.trigger_config)
    if body.script is not None:
        automation.script = body.script
    if body.status is not None:
        automation.status = body.status
    await session.commit()
    await session.refresh(automation)
    return _to_response(automation)


@router.delete("/{automation_id}", status_code=204)
async def delete_automation(
    automation_id: str,
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
):
    automation = await session.get(Automation, automation_id)
    if not automation or automation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Automation not found")
    await session.delete(automation)
    await session.commit()


@router.post("/{automation_id}/run")
async def run_automation_now(
    automation_id: str,
    user_id: str = Depends(_get_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Execute an automation immediately."""
    automation = await session.get(Automation, automation_id)
    if not automation or automation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Automation not found")

    from app.automation.sandbox import execute_script
    from app.automation.context import AutomationContext
    import traceback

    ctx = AutomationContext(user_id=user_id, automation_id=automation_id)
    try:
        result = await execute_script(automation.script, ctx)
        automation.last_result = result
        automation.last_error = None
        automation.status = "active"
    except Exception as e:
        automation.last_error = traceback.format_exc()
        automation.last_result = None
        automation.status = "error"

    automation.last_run = datetime.utcnow()
    automation.run_count += 1
    await session.commit()
    await session.refresh(automation)
    return _to_response(automation)


def _to_response(a: Automation) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "trigger_type": a.trigger_type,
        "trigger_config": json.loads(a.trigger_config) if isinstance(a.trigger_config, str) else a.trigger_config,
        "script": a.script,
        "status": a.status,
        "last_run": a.last_run,
        "last_result": a.last_result,
        "last_error": a.last_error,
        "run_count": a.run_count,
    }
