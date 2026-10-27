"""QuorumPilot - orchestration.

PERCEIVE -> SPECIALIZE -> VERIFY -> ARBITRATE -> EXPLAIN -> RECEIPT

The only place a decision is made is ARBITRATE, and it may only read claims
that survived VERIFY.
"""

import time
from typing import Any, Dict, List, Optional

from .arbitrate import arbitrate
from .brain import Brain, get_brain
from .market import (Snapshot, compute_metrics, parse_snapshot, policy_check,
                     corr_to)
from .agents import run_specialists
from .verify import fact_bundle, verify_claims


def _stage(trace: List[Dict[str, Any]], stage: str, detail: str) -> None:
    trace.append({"stage": stage, "detail": detail})


def review(payload: Any, brain: Optional[Brain] = None,
           prefer_llm: bool = True) -> Dict[str, Any]:
    brain = brain or get_brain(prefer_llm=prefer_llm)
    trace: List[Dict[str, Any]] = []
    t0 = time.time()

    snap: Snapshot = parse_snapshot(payload)
    _stage(trace, "PERCEIVE",
           "parsed account (%d positions, %.2f %s equity) and proposal %s %s"
           % (len(snap.account.positions), snap.account.equity,
              snap.account.currency, snap.proposal.side,
              snap.proposal.symbol or "?"))
    for w in snap.warnings:
        _stage(trace, "PERCEIVE", "warning: %s" % w)

    m = compute_metrics(snap)
    bundle = fact_bundle(snap, m)
    breaches = policy_check(m, snap.policy)
    _stage(trace, "PERCEIVE",
           "computed %d facts, %d policy breach(es)"
           % (len(bundle), len(breaches)))

    claims = run_specialists(snap, m, breaches)
    _stage(trace, "SPECIALIZE",
           "4 specialists proposed %d claims" % len(claims))

    extra = brain.propose(snap, m, bundle)
    if extra:
        claims = claims + extra
        _stage(trace, "SPECIALIZE",
               "%s added %d claim(s)" % (brain.name, len(extra)))
    elif brain.degraded:
        _stage(trace, "SPECIALIZE",
               "%s unavailable (%s); deterministic quorum only"
               % (brain.name, getattr(brain, "error", "?")))
    else:
        _stage(trace, "SPECIALIZE", "no LLM configured; deterministic quorum")

    verified, dropped = verify_claims(claims, bundle)
    _stage(trace, "VERIFY",
           "%d verified, %d dropped for unprovable evidence"
           % (len(verified), len(dropped)))

    decision = arbitrate(snap, m, verified, dropped, breaches)
    _stage(trace, "ARBITRATE",
           "%s (score %d, %d objection(s))"
           % (decision["verdict"], decision["score"],
              decision["tally"]["objection"]))

    _stage(trace, "EXPLAIN", decision["explain"][:160])

    receipt = {
        "tool": "quorumpilot.review_trade",
        "input": {
            "symbol": snap.proposal.symbol,
            "side": snap.proposal.side,
            "units": snap.proposal.units,
            "positions_parsed": len(snap.account.positions),
            "equity": snap.account.equity,
        },
        "output": {
            "verdict": decision["verdict"],
            "suggested_units": decision["suggested_units"],
            "risk_pct": decision["risk_pct"],
            "claims_verified": decision["claims_verified"],
            "claims_dropped": decision["claims_dropped"],
        },
        "verdict": decision["verdict"],
        "brain": brain.name,
        "brain_degraded": bool(brain.degraded),
        "duration_ms": int((time.time() - t0) * 1000),
        "trace": trace,
    }
    _stage(trace, "RECEIPT", "decision recorded with %d trace stages"
           % (len(trace) + 1))

    return {
        "snapshot": snap,
        "metrics": m,
        "breaches": breaches,
        "claims": claims,
        "verified": verified,
        "dropped": dropped,
        "decision": decision,
        "receipt": receipt,
    }
