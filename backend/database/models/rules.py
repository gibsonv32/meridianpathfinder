from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.models.base import Base


class Threshold(Base):
    __tablename__ = "thresholds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="USD")
    effective_date: Mapped[date] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    authority: Mapped[str] = mapped_column(String(255))
    overlay_level: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ApprovalLadder(Base):
    __tablename__ = "approval_ladders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_type: Mapped[str] = mapped_column(String(50), index=True)
    min_value: Mapped[float] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    approver_role: Mapped[str] = mapped_column(String(100))
    authority: Mapped[str] = mapped_column(String(255))
    effective_date: Mapped[date] = mapped_column(Date)


class QCodeNode(Base):
    __tablename__ = "qcode_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    question_text: Mapped[str] = mapped_column(Text)
    branch_logic_json: Mapped[str] = mapped_column(Text, default="{}")
    triggered_dcodes: Mapped[str] = mapped_column(Text)
    system_behavior: Mapped[str] = mapped_column(Text)
    authority: Mapped[str] = mapped_column(String(255))
    confidence_level: Mapped[str] = mapped_column(String(20), default="high")


class DCode(Base):
    __tablename__ = "dcodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    always_required: Mapped[bool] = mapped_column(Boolean, default=False)
    condition_text: Mapped[str] = mapped_column(Text)
