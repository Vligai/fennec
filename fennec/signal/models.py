import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Verdict(Base):
    """Developer verdict on a finding — the core signal store record."""

    __tablename__ = "verdicts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    path_hash = Column(String, nullable=False, index=True)
    verdict = Column(String, nullable=False)  # real_vuln | false_positive | wont_fix
    reviewer_id = Column(String, nullable=False)
    repo_id = Column(String, nullable=False)
    service_id = Column(String, nullable=False)
    org_id = Column(String, nullable=False, index=True)
    pattern_fingerprint = Column(String, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class SanitizerTrust(Base):
    """Pre-computed org-scoped sanitizer trust; populated by the propagation job."""

    __tablename__ = "sanitizer_trust"
    __table_args__ = (UniqueConstraint("pattern", "org_id", name="uq_sanitizer_trust_pattern_org"),)

    id = Column(String, primary_key=True)  # stable: f"{pattern}|{org_id}"
    pattern = Column(String, nullable=False)
    taint_type = Column(String, nullable=False, default="")
    org_id = Column(String, nullable=False, index=True)
    trust_score = Column(Float, nullable=False, default=0.0)
    verdict_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False)
