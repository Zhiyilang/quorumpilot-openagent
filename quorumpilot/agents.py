"""The quorum: four specialists, each of which must show its work.

Every specialist returns *claims*, not verdicts. A claim is a stance plus
citations into the fact bundle. Nothing here decides anything - the arbiter
does that, after the verifier has thrown away whatever cannot be proven.
"""

from typing import Any, Dict, List

from .market import corr_to

STANCE_WEIGHT = {"support": 1, "caution": -2, "objection": -4}


def _money(v: float) -> str:
    return "%.2f" % v


def _pct(v: float) -> str:
    return "%.2f" % v


def _ev(locator: str, excerpt: str, source: str = "metrics") -> Dict[str, str]:
    return {"source": source, "locator": locator, "excerpt": excerpt}


def _claim(agent: str, n: int, statement: str, stance: str,
           evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    return {
        "id": "%s-%d" % (agent, n),
        "agent": agent,
        "statement": statement,
        "stance": stance,
        "evidence": evidence,
    }


# ------------------------------------------------------------------ specialists

def analyst(snap, m, bundle) -> List[Dict[str, Any]]:
    out, n = [], 0
    symbol = m["proposal.symbol"]
    if m["metrics.rr_ratio"]:
        n += 1
        good = m["metrics.rr_ratio"] >= (snap.policy.get("min_rr_ratio") or 0)
        out.append(_claim(
            "analyst", n,
            "Reward:risk on %s is %.2f against a %.2f minimum."
            % (symbol, m["metrics.rr_ratio"], snap.policy.get("min_rr_ratio") or 0),
            "support" if good else "caution",
            [_ev("metrics.rr_ratio", "%.2f" % m["metrics.rr_ratio"]),
             _ev("policy.min_rr_ratio",
                 "%.2f" % (snap.policy.get("min_rr_ratio") or 0), "policy")]))
    if m["metrics.stop_distance"]:
        n += 1
        wide = m["metrics.stop_pct_of_price"] > (
            snap.policy.get("max_stop_pct_of_price") or 100)
        out.append(_claim(
            "analyst", n,
            "The stop sits %.2f%% away from entry, which is %s for a %d-day hold."
            % (m["metrics.stop_pct_of_price"],
               "wide" if wide else "tight enough",
               m["proposal.horizon_days"]),
            "caution" if wide else "support",
            [_ev("metrics.stop_pct_of_price",
                 "%.2f" % m["metrics.stop_pct_of_price"]),
             _ev("proposal.horizon_days",
                 "%d" % m["proposal.horizon_days"])]))
    if not m["metrics.risk_amount"]:
        n += 1
        out.append(_claim(
            "analyst", n,
            "The proposal has no stop, so the downside is unbounded and the "
            "reward:risk cannot be computed.",
            "objection", [_ev("proposal.stop", "None")]))
    return out


def skeptic(snap, m, bundle) -> List[Dict[str, Any]]:
    out, n = [], 0
    symbol = m["proposal.symbol"]
    if m["metrics.correlated_with"]:
        n += 1
        out.append(_claim(
            "skeptic", n,
            "%s is already exposed to %s, so this trade adds to the same bet "
            "rather than diversifying."
            % (symbol, ", ".join(m["metrics.correlated_with"])),
            "objection" if m["metrics.correlated_risk_pct"] > (
                snap.policy.get("max_correlated_risk_pct") or 1e9) else "caution",
            [_ev("metrics.correlated_risk_pct",
                 "%.2f" % m["metrics.correlated_risk_pct"]),
             _ev("metrics.correlated_with",
                 str(m["metrics.correlated_with"])[:60])]))
    same_side = [p for p in snap.account.positions
                 if p.symbol == symbol or corr_to(symbol, p.symbol,
                                                  snap.correlations) >= 0.7]
    if len(same_side) >= 2:
        n += 1
        out.append(_claim(
            "skeptic", n,
            "%d open positions already lean the same way as this idea; a single "
            "macro surprise would hit all of them at once." % len(same_side),
            "caution",
            [_ev("account.open_positions",
                 "%d" % m["account.open_positions"])]))
    if m["metrics.effective_leverage"] > (snap.policy.get("max_leverage") or 1e9):
        n += 1
        out.append(_claim(
            "skeptic", n,
            "Effective leverage of %.2f on this ticket alone is above the "
            "%.2f cap - the position is large relative to the account, not "
            "just relative to the stop."
            % (m["metrics.effective_leverage"], snap.policy.get("max_leverage")),
            "objection",
            [_ev("metrics.effective_leverage",
                 "%.2f" % m["metrics.effective_leverage"]),
             _ev("policy.max_leverage",
                 "%.2f" % snap.policy.get("max_leverage"), "policy")]))
    if m["metrics.free_margin_pct_after"] < (
            snap.policy.get("min_free_margin_pct") or 0):
        n += 1
        out.append(_claim(
            "skeptic", n,
            "After this ticket, free margin would be %.2f%% of equity; there "
            "would be little room to defend the book if it moves against you."
            % m["metrics.free_margin_pct_after"],
            "objection",
            [_ev("metrics.free_margin_pct_after",
                 "%.2f" % m["metrics.free_margin_pct_after"])]))
    if not out:
        n += 1
        out.append(_claim(
            "skeptic", n,
            "No concentration, correlation or margin objection survives the "
            "numbers on this ticket.",
            "support",
            [_ev("metrics.correlated_risk_pct",
                 "%.2f" % m["metrics.correlated_risk_pct"])]))
    return out


def risk(snap, m, bundle) -> List[Dict[str, Any]]:
    out = []
    n = 0
    n += 1
    out.append(_claim(
        "risk", n,
        "Cash at risk is %s %s, which is %.2f%% of equity."
        % (_money(m["metrics.risk_amount"]), m["account.currency"],
           m["metrics.risk_pct"]),
        "objection" if m["metrics.risk_pct"] > (
            snap.policy.get("max_risk_pct_per_trade") or 1e9) else "support",
        [_ev("metrics.risk_amount", _money(m["metrics.risk_amount"])),
         _ev("metrics.risk_pct", _pct(m["metrics.risk_pct"])),
         _ev("account.equity", _money(m["account.equity"]))]))
    cap_total = float(snap.policy.get("max_total_risk_pct") or 0)
    usage = (m["metrics.total_risk_pct"] / cap_total) if cap_total else 0.0
    n += 1
    out.append(_claim(
        "risk", n,
        "If every stop on the book is hit, equity falls to %s - a %.2f%% "
        "drawdown, which is %.0f%% of the portfolio risk budget."
        % (_money(m["metrics.worst_case_equity"]),
           m["metrics.worst_case_drawdown_pct"], 100 * usage),
        "objection" if usage > 1 else ("caution" if usage >= 0.5 else "support"),
        [_ev("metrics.worst_case_equity",
             _money(m["metrics.worst_case_equity"])),
         _ev("metrics.total_risk_pct", _pct(m["metrics.total_risk_pct"])),
         _ev("policy.max_total_risk_pct",
             _pct(snap.policy.get("max_total_risk_pct")), "policy")]))

    floor = float(snap.policy.get("min_free_margin_pct") or 0)
    after = m["metrics.free_margin_pct_after"]
    n += 1
    out.append(_claim(
        "risk", n,
        "Margin required is %s, leaving %s free (%.2f%% of equity)."
        % (_money(m["metrics.margin_required"]),
           _money(m["metrics.free_margin_after"]), after),
        ("objection" if after < floor
         else "caution" if after < 2 * floor else "support"),
        [_ev("metrics.margin_required", _money(m["metrics.margin_required"])),
         _ev("metrics.free_margin_after",
             _money(m["metrics.free_margin_after"])),
         _ev("metrics.free_margin_pct_after", _pct(after))]))
    return out


def compliance(snap, m, breaches) -> List[Dict[str, Any]]:
    if breaches:
        out = []
        for i, b in enumerate(breaches, start=1):
            out.append({
                "id": "compliance-%d" % i,
                "agent": "compliance",
                "statement": "[%s] %s" % (b["rule"], b["detail"]),
                "stance": "objection" if b["severity"] == "hard" else "caution",
                "evidence": b["evidence"],
            })
        return out
    return [{
        "id": "compliance-1",
        "agent": "compliance",
        "statement": "No policy rule is breached by this ticket.",
        "stance": "support",
        "evidence": [_ev("metrics.risk_pct", _pct(m["metrics.risk_pct"])),
                     _ev("policy.max_risk_pct_per_trade",
                         _pct(snap.policy.get("max_risk_pct_per_trade")
                              or 0), "policy")],
    }]


SPECIALISTS = {
    "analyst": analyst,
    "skeptic": skeptic,
    "risk": risk,
}


def run_specialists(snap, m, breaches) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    for name, fn in SPECIALISTS.items():
        claims.extend(fn(snap, m, {}))
    claims.extend(compliance(snap, m, breaches))
    for c in claims:
        c["weight"] = STANCE_WEIGHT.get(c["stance"], 0)
        c["proposed_by"] = c["agent"]
    return claims
