from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON, DateTime, LargeBinary, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .db import Base

class Image(Base):
    __tablename__ = "images"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    url_original: Mapped[str] = mapped_column(Text)
    url_redacted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pipeline_versions: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)

    regions: Mapped[list["Region"]] = relationship("Region", back_populates="image", cascade="all, delete-orphan")

class Region(Base):
    __tablename__ = "regions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    image_id: Mapped[str] = mapped_column(String, ForeignKey("images.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String)
    polygon_json: Mapped[str] = mapped_column(Text)  # store as JSON string
    confidence: Mapped[float] = mapped_column(Float)

    sha256: Mapped[str] = mapped_column(String)
    enc_algo: Mapped[str] = mapped_column(String)  # e.g., AES-GCM
    iv_hex: Mapped[str] = mapped_column(String)
    kms_key_id: Mapped[str | None] = mapped_column(String, nullable=True)

    image: Mapped["Image"] = relationship("Image", back_populates="regions")

class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)  # VIEW|DECRYPT|INGEST
    image_id: Mapped[str] = mapped_column(String)
    region_id: Mapped[str | None] = mapped_column(String, nullable=True)
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    model_versions: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
