import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from .models import Base, SanitizerTrust, Verdict


def compute_path_hash(function_ids: list[str]) -> str:
    """SHA-256 of the sorted function ID list — stable across insertion order."""
    combined = ",".join(sorted(function_ids))
    return hashlib.sha256(combined.encode()).hexdigest()


class SignalStore:
    def __init__(self, db_url: str) -> None:
        self._engine = create_engine(db_url)
        Base.metadata.create_all(self._engine)

    # ------------------------------------------------------------------ #
    # Writes                                                               #
    # ------------------------------------------------------------------ #

    def write_verdict(self, verdict: dict) -> None:
        """Insert a verdict record. Required keys: path_hash, verdict,
        reviewer_id, repo_id, service_id, org_id, pattern_fingerprint."""
        row = Verdict(
            id=verdict.get("id", str(uuid.uuid4())),
            path_hash=verdict["path_hash"],
            verdict=verdict["verdict"],
            reviewer_id=verdict["reviewer_id"],
            repo_id=verdict["repo_id"],
            service_id=verdict["service_id"],
            org_id=verdict["org_id"],
            pattern_fingerprint=verdict["pattern_fingerprint"],
            created_at=verdict.get("created_at", datetime.now(timezone.utc)),
        )
        with Session(self._engine) as session:
            session.add(row)
            session.commit()

    # ------------------------------------------------------------------ #
    # Reads                                                                #
    # ------------------------------------------------------------------ #

    def is_suppressed(self, path_hash: str) -> bool:
        """Return True if any active wont_fix verdict exists for this path_hash."""
        with Session(self._engine) as session:
            count = session.execute(
                select(func.count())
                .select_from(Verdict)
                .where(Verdict.path_hash == path_hash, Verdict.verdict == "wont_fix")
            ).scalar()
            return (count or 0) > 0

    def get_trust_scores(self, org_id: str) -> dict[str, float]:
        """Return pattern → trust_score for all org-scoped sanitizer trust entries.

        Reads from the pre-computed sanitizer_trust table (populated by PropagationJob).
        wont_fix verdicts never enter this table by design.
        """
        with Session(self._engine) as session:
            rows = session.execute(
                select(SanitizerTrust.pattern, SanitizerTrust.trust_score).where(
                    SanitizerTrust.org_id == org_id
                )
            ).all()
            return {row.pattern: row.trust_score for row in rows}
