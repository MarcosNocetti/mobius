import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    api_keys: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
