from app.agents.tools.decorator import tool_action


@tool_action(
    name="create_automation",
    description="Create a new automation. Provide the Python script that uses ctx.tools.* and ctx.ai.* to perform actions. The script must define an async function `run(ctx)` that will be called on each execution.",
    integration="_system",
    params={
        "name": {"type": "string", "description": "Automation name"},
        "description": {"type": "string", "description": "What this automation does"},
        "cron": {"type": "string", "description": "Cron expression (e.g. '0 9 * * *' for daily 9am)"},
        "script": {"type": "string", "description": "Python script source code"},
    },
)
async def create_automation_tool(user_id: str, name: str, description: str, cron: str, script: str) -> str:
    from app.core.database import AsyncSessionLocal
    from app.models.automation import Automation
    import json

    async with AsyncSessionLocal() as session:
        automation = Automation(
            user_id=user_id,
            name=name,
            description=description,
            trigger_type="cron",
            trigger_config=json.dumps({"cron": cron}),
            script=script,
            status="active",
        )
        session.add(automation)
        await session.commit()
        await session.refresh(automation)
        return f"Automation '{name}' created (ID: {automation.id}). Cron: {cron}. Status: active."


@tool_action(
    name="list_automations",
    description="List all automations for the current user with their status.",
    integration="_system",
    params={},
)
async def list_automations_tool(user_id: str) -> str:
    from app.core.database import AsyncSessionLocal
    from app.models.automation import Automation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Automation).where(Automation.user_id == user_id)
        )
        automations = result.scalars().all()

    if not automations:
        return "No automations configured."

    lines = []
    for a in automations:
        lines.append(f"- {a.name} [{a.status}] (ID: {a.id}) — {a.description}")
    return "\n".join(lines)


@tool_action(
    name="run_automation_now",
    description="Trigger immediate execution of an automation by its ID.",
    integration="_system",
    params={
        "automation_id": {"type": "string", "description": "Automation ID to execute"},
    },
)
async def run_automation_now_tool(user_id: str, automation_id: str) -> str:
    from app.core.database import AsyncSessionLocal
    from app.models.automation import Automation
    from app.automation.sandbox import execute_script
    from app.automation.context import AutomationContext
    import traceback
    from datetime import datetime

    async with AsyncSessionLocal() as session:
        automation = await session.get(Automation, automation_id)
        if not automation or automation.user_id != user_id:
            return "Automation not found."

        ctx = AutomationContext(user_id=user_id, automation_id=automation_id)
        try:
            result = await execute_script(automation.script, ctx)
            automation.last_result = result
            automation.last_error = None
            automation.status = "active"
        except Exception as e:
            automation.last_error = traceback.format_exc()
            automation.status = "error"
            result = f"Error: {e}"

        automation.last_run = datetime.utcnow()
        automation.run_count += 1
        await session.commit()
        return f"Automation '{automation.name}' executed. Result: {result}"
