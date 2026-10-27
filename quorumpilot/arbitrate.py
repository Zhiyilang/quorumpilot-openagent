"""The arbiter: turns verified claims into one decision.

It never invents a number. It reads the verified claims, applies the rule
breaches (which are pure arithmetic), and - when a cap is binding - solves
for the largest position that would fit inside the rules.
"""

from typing import Any, Dict, List, Optional

from .market import Snapshot, solve_units_for_risk

VERDICTS = ("PROCEED", "PROCEED_WITH_CAUTION", "REJECT")


def tally(claims: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {"support": 0, "caution": 0, "objection": 0}
    for c in claims:
        out[c["stance"]] = out.get(c["stance"], 0) + 1
    return out


def suggest_units(snap: Snapshot, m: Dict[str, Any],
                  breaches: List[Dict[str, Any]]) -> Optional[float]:
    """Largest unit count that would satisfy every binding cap."""
    if not breaches or not m["proposal.units"]:
        return None
    pol, acct, prop = snap.policy, snap.account, snap.proposal
    entry = prop.entry
    if not entry:
        return None
    candidates: List[float] = []
    rules = {b["rule"] for b in breaches}

    if "RISK_PER_TRADE" in rules or "TOTAL_RISK" in rules:
        cap = float(pol.get("max_risk_pct_per_trade") or 0)
        if "TOTAL_RISK" in rules:
            # share the portfolio cap with what is already open
            headroom = max(0.0, float(pol.get("max_total_risk_pct") or 0)
                           - m["metrics.open_risk_pct"])
            cap = min(cap, headroom) if cap else headroom
        u = solve_units_for_risk(snap, cap)
        if u > 0:
            candidates.append(u)

    if "LEVERAGE" in rules:
        cap_lev = float(pol.get("max_leverage") or 0)
        if cap_lev:
            candidates.append(max(0.0, acct.equity * cap_lev / entry))

    # risk-based caps: each unit adds (stop distance / equity) percentage points
    per_unit_risk_pct = (100.0 * m["metrics.stop_distance"] / acct.equity
                         if acct.equity else 0.0)
    if per_unit_risk_pct > 0:
        for rule, pct_key, cap_key in (
                ("RISK_CONCENTRATION", "metrics.risk_concentration_pct",
                 "max_risk_concentration_pct"),
                ("CORRELATED_RISK", "metrics.correlated_risk_pct",
                 "max_correlated_risk_pct")):
            if rule not in rules:
                continue
            cap_pct = float(pol.get(cap_key) or 0)
            if not cap_pct:
                continue
            already_pct = (m[pct_key]
                           - m["proposal.units"] * per_unit_risk_pct)
            candidates.append(max(0.0, (cap_pct - already_pct)
                                 / per_unit_risk_pct))

    if not candidates:
        return None
    units = min(candidates)
    units = float(int(units))
    if units <= 0 or units >= m["proposal.units"]:
        return None
    return units


def arbitrate(snap: Snapshot, m: Dict[str, Any],
              verified: List[Dict[str, Any]],
              dropped: List[Dict[str, Any]],
              breaches: List[Dict[str, Any]]) -> Dict[str, Any]:
    t = tally(verified)
    score = sum(c.get("weight", 0) for c in verified)
    hard = [b for b in breaches if b["severity"] == "hard"]

    if hard:
        verdict = "REJECT"
    elif t["objection"]:
        verdict = "REJECT"
    elif score < 0:
        verdict = "PROCEED_WITH_CAUTION"
    else:
        verdict = "PROCEED"

    units = suggest_units(snap, m, breaches)
    actions: List[str] = []
    for b in breaches:
        actions.append("%s: %s" % (b["rule"], b["detail"]))
    if units:
        actions.insert(0, "Reduce size to %.0f units to fit inside the rules."
                       % units)
    if verdict == "PROCEED":
        actions.append("No rule blocks the ticket. Size is inside every cap.")

    explain = _explain(verdict, verified, breaches, units, m)
    return {
        "verdict": verdict,
        "score": score,
        "tally": t,
        "claims_total": len(verified) + len(dropped),
        "claims_verified": len(verified),
        "claims_dropped": len(dropped),
        "dropped": [{"id": d.get("id"), "agent": d.get("agent"),
                     "statement": d.get("statement"),
                     "reasons": d.get("_reasons")} for d in dropped],
        "breaches": breaches,
        "suggested_units": units,
        "required_actions": actions,
        "explain": explain,
        "symbol": m["proposal.symbol"],
        "side": m["proposal.side"],
        "risk_pct": m["metrics.risk_pct"],
        "risk_amount": m["metrics.risk_amount"],
        "worst_case_equity": m["metrics.worst_case_equity"],
    }


def _explain(verdict: str, verified: List[Dict[str, Any]],
             breaches: List[Dict[str, Any]],
             units: Optional[float], m: Dict[str, Any]) -> str:
    symbol = m["proposal.symbol"]
    head = {
        "PROCEED": "The quorum clears %s." % symbol,
        "PROCEED_WITH_CAUTION": "The quorum lets %s through with reservations."
                                % symbol,
        "REJECT": "The quorum blocks %s." % symbol,
    }[verdict]
    bits = [head]
    if breaches:
        bits.append("%d rule%s breached: %s."
                    % (len(breaches), "" if len(breaches) == 1 else "s",
                       ", ".join(b["rule"] for b in breaches)))
    objections = [c["statement"] for c in verified if c["stance"] == "objection"]
    if objections:
        bits.append(objections[0])
    cautions = [c["statement"] for c in verified if c["stance"] == "caution"]
    if cautions:
        bits.append(cautions[0])
    if units and m["account.equity"]:
        new_risk_pct = 100.0 * m["metrics.stop_distance"] * units / m["account.equity"]
        bits.append("At %.0f units the risk would be %.2f%% of equity instead "
                    "of %.2f%%." % (units, new_risk_pct, m["metrics.risk_pct"]))
    return " ".join(bits)
