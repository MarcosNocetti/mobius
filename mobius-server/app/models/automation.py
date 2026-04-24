import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Automation(Base):
    __tablename__ = "automations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    trigger_type: Mapped[str] = mapped_column(String, default="cron")  # "cron" | "manual" | "webhook"
    trigger_config: Mapped[str] = mapped_column(Text, default="{}")  # JSON: {"cron": "0 9 * * *"}
    script: Mapped[str] = mapped_column(Text, default="")  # Python source code
    status: Mapped[str] = mapped_column(String, default="draft")  # "draft" | "active" | "paused" | "error"
    last_run: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Backward-compat alias
ScheduledAutomation = Automation
