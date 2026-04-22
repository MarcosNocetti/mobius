from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from jose import JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.database import get_session
from app.core.security import decode_token
from app.models.automation import ScheduledAutomation

router = APIRouter(prefix="/automations", tags=["automations"])
bearer = HTTPBearer()


async def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        return decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class AutomationCreate(BaseModel):
    prompt: str
    cron_expr: str


class AutomationResponse(BaseModel):
    id: str
    prompt: str
    cron_expr: str
    active: bool
    user_id: str


@router.post("", response_model=AutomationResponse, status_code=201)
async def create_automation(
    body: AutomationCreate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    auto = ScheduledAutomation(user_id=user_id, prompt=body.prompt, cron_expr=body.cron_expr)
    session.add(auto)
    await session.commit()
    await session.refresh(auto)
    return AutomationResponse(id=auto.id, prompt=auto.prompt, cron_expr=auto.cron_expr, active=auto.active, user_id=auto.user_id)


@router.get("", response_model=list[AutomationResponse])
async def list_automations(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(ScheduledAutomation).where(ScheduledAutomation.user_id == user_id))
    autos = result.scalars().all()
    return [AutomationResponse(id=a.id, prompt=a.prompt, cron_expr=a.cron_expr, active=a.active, user_id=a.user_id) for a in autos]


@router.delete("/{automation_id}", status_code=204)
async def delete_automation(
    automation_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    auto = await session.get(ScheduledAutomation, automation_id)
    if not auto or auto.user_id != user_id:
        raise HTTPException(status_code=404, detail="Automation not found")
    await session.delete(auto)
    await session.commit()
