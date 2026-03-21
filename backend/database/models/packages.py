from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.models.base import Base


class AcquisitionPackage(Base):
    __tablename__ = "acquisition_packages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    value: Mapped[float] = mapped_column(Float)
    naics: Mapped[str] = mapped_column(String(20))
    psc: Mapped[str] = mapped_column(String(20))
    services: Mapped[bool] = mapped_column(Boolean, default=False)
    it_related: Mapped[bool] = mapped_column(Boolean, default=False)
    sole_source: Mapped[bool] = mapped_column(Boolean, default=False)
    commercial_item: Mapped[bool] = mapped_column(Boolean, default=False)
    emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    vendor_on_site: Mapped[bool] = mapped_column(Boolean, default=False)
    competition_type: Mapped[str] = mapped_column(String(50), default="full_and_open")
    phase: Mapped[str] = mapped_column(String(100), default="Intake")
    status: Mapped[str] = mapped_column(String(20), default="action")
    blocking_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[str] = mapped_column(String(20), default="2026-03-31")
    posting_deadline_days: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    documents: Mapped[list[PackageDocument]] = relationship(back_populates="package", cascade="all, delete-orphan")


class PackageDocument(Base):
    __tablename__ = "package_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package_id: Mapped[str] = mapped_column(ForeignKey("acquisition_packages.id", ondelete="CASCADE"), index=True)
    dcode: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="missing")
    responsible_party: Mapped[str] = mapped_column(String(100), default="CO")
    source_attribution: Mapped[str | None] = mapped_column(Text, nullable=True)

    package: Mapped[AcquisitionPackage] = relationship(back_populates="documents")
