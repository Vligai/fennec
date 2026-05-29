"""Fennec hosted service API — org rule storage and retrieval."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from fennec.signal.models import Base, OrgRuleRow

app = FastAPI(title="Fennec Org Rule API", version="1.0.0")

# In-memory admin key set for v1 (production: user role DB lookup)
_ADMIN_API_KEYS: set[str] = {"admin-secret-key"}


def _get_engine(db_url: str = "sqlite:///./fennec_signals.db"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


# Dependency: application engine (overridable in tests)
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _get_engine()
    return _engine


# ------------------------------------------------------------------ #
# Pydantic schemas (privacy boundary: no code/paths/traces)          #
# ------------------------------------------------------------------ #

class OrgRuleRequest(BaseModel):
    type: str           # source | sink | sanitizer
    pattern: str
    taint_type: str = ""
    scope_glob: str = ""
    mode: str = "advisory"


class OrgRuleResponse(BaseModel):
    rule_id: str
    org_id: str
    type: str
    pattern: str
    taint_type: str
    scope_glob: str
    mode: str
    created_by: str
    created_at: str


def _row_to_response(row: OrgRuleRow) -> OrgRuleResponse:
    return OrgRuleResponse(
        rule_id=row.rule_id,
        org_id=row.org_id,
        type=row.type,
        pattern=row.pattern,
        taint_type=row.taint_type,
        scope_glob=row.scope_glob,
        mode=row.mode,
        created_by=row.created_by,
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


# ------------------------------------------------------------------ #
# Auth dependencies                                                   #
# ------------------------------------------------------------------ #

def _require_api_key(x_fennec_api_key: Annotated[str | None, Header()] = None) -> str:
    if not x_fennec_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    return x_fennec_api_key


def _require_admin(api_key: str = Depends(_require_api_key)) -> str:
    if api_key not in _ADMIN_API_KEYS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return api_key


# ------------------------------------------------------------------ #
# Endpoints                                                            #
# ------------------------------------------------------------------ #

@app.get("/api/v1/org/{org_id}/rules", response_model=list[OrgRuleResponse])
def get_org_rules(
    org_id: str,
    api_key: str = Depends(_require_api_key),
    engine=Depends(get_engine),
) -> list[OrgRuleResponse]:
    with Session(engine) as session:
        rows = session.execute(
            select(OrgRuleRow).where(OrgRuleRow.org_id == org_id)
        ).scalars().all()
        return [_row_to_response(r) for r in rows]


@app.post("/api/v1/org/{org_id}/rules", response_model=OrgRuleResponse, status_code=201)
def create_org_rule(
    org_id: str,
    rule: OrgRuleRequest,
    api_key: str = Depends(_require_admin),
    engine=Depends(get_engine),
) -> OrgRuleResponse:
    if not rule.pattern.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="pattern is required")

    row = OrgRuleRow(
        rule_id=str(uuid.uuid4()),
        org_id=org_id,
        type=rule.type,
        pattern=rule.pattern,
        taint_type=rule.taint_type,
        scope_glob=rule.scope_glob,
        mode=rule.mode,
        created_by=api_key,
        created_at=datetime.now(timezone.utc),
    )
    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return _row_to_response(row)
