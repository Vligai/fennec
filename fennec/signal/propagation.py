from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import SanitizerTrust, Verdict
from .store import SignalStore


class PropagationJob:
    """Async batch job that recomputes sanitizer_trust from accumulated verdicts.

    A pattern earns org-scoped trust only when it has >= threshold false_positive
    verdicts spread across >= 2 distinct services. Single-service patterns stay
    at service scope (i.e. no sanitizer_trust row is written for them).
    """

    def __init__(self, store: SignalStore) -> None:
        self._store = store

    def run(self, org_id: str, threshold: int = 3) -> None:
        engine = self._store._engine
        now = datetime.now(timezone.utc)

        with Session(engine) as session:
            # Aggregate false_positive verdicts per pattern for this org.
            fp_rows = session.execute(
                select(
                    Verdict.pattern_fingerprint,
                    func.count(Verdict.id).label("fp_count"),
                    func.count(Verdict.service_id.distinct()).label("service_count"),
                )
                .where(
                    Verdict.org_id == org_id,
                    Verdict.verdict == "false_positive",
                )
                .group_by(Verdict.pattern_fingerprint)
            ).all()

            for row in fp_rows:
                # Cross-service threshold check — single-service patterns are not propagated.
                if row.fp_count < threshold or row.service_count < 2:
                    continue

                # Total non-wont_fix verdicts for this pattern (denominator for trust score).
                total = session.execute(
                    select(func.count())
                    .select_from(Verdict)
                    .where(
                        Verdict.org_id == org_id,
                        Verdict.pattern_fingerprint == row.pattern_fingerprint,
                        Verdict.verdict != "wont_fix",
                    )
                ).scalar() or 0

                trust_score = row.fp_count / total if total > 0 else 0.0
                trust_id = f"{row.pattern_fingerprint}|{org_id}"

                trust = session.get(SanitizerTrust, trust_id)
                if trust is None:
                    trust = SanitizerTrust(
                        id=trust_id,
                        pattern=row.pattern_fingerprint,
                        taint_type="",
                        org_id=org_id,
                    )
                trust.trust_score = trust_score
                trust.verdict_count = row.fp_count
                trust.updated_at = now
                session.merge(trust)

            session.commit()
