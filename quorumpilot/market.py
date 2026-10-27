"""Deterministic market facts.

Everything in this module is arithmetic. No model, no opinion, no network.
The agents are only allowed to *quote* from the flat fact bundle produced
here, and the verifier (``verify.py``) re-resolves every locator they cite.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_POLICY = {
    "max_risk_pct_per_trade": 2.0,
    "max_total_risk_pct": 6.0,
    "max_leverage": 30.0,
    "max_risk_concentration_pct": 4.0,
    "max_correlated_risk_pct": 5.0,
    "min_rr_ratio": 1.5,
    "max_positions": 8,
    "min_free_margin_pct": 20.0,
    "restricted_symbols": [],
    "max_stop_pct_of_price": 8.0,
}


@dataclass
class Position:
    symbol: str
    side: str
    units: float
    entry: float
    stop: Optional[float] = None
    current: Optional[float] = None

    @property
    def risk_amount(self) -> float:
        if not self.stop or self.entry <= 0:
            return 0.0
        return abs(self.entry - self.stop) * abs(self.units)

    @property
    def notional(self) -> float:
        return abs(self.units) * self.entry


@dataclass
class Proposal:
    symbol: str = ""
    side: str = "long"
    units: float = 0.0
    entry: float = 0.0
    stop: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: float = 1.0
    horizon_days: int = 1


@dataclass
class Account:
    currency: str = "USD"
    equity: float = 0.0
    free_margin: float = 0.0
    used_margin: float = 0.0
    positions: List[Position] = field(default_factory=list)


@dataclass
class Snapshot:
    account: Account
    proposal: Proposal
    policy: Dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_POLICY))
    correlations: Dict[str, Dict[str, float]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


# --------------------------------------------------------------------- parsing

def _num(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("$", "").replace("%", "")
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        val = float(s)
    except ValueError:
        return None
    return -val if neg else val


def _position_from(d: Dict[str, Any]) -> Optional[Position]:
    symbol = str(d.get("symbol") or d.get("instrument") or "").strip().upper()
    units = _num(d.get("units") or d.get("size") or d.get("volume"))
    entry = _num(d.get("entry") or d.get("entry_price") or d.get("open_price"))
    if not symbol or units is None or entry is None or entry <= 0:
        return None
    side = str(d.get("side") or d.get("direction") or "").strip().lower()
    if side not in ("long", "short", "buy", "sell"):
        side = "long" if units > 0 else "short"
    side = "long" if side in ("long", "buy") else "short"
    return Position(
        symbol=symbol,
        side=side,
        units=abs(units),
        entry=entry,
        stop=_num(d.get("stop") or d.get("stop_loss") or d.get("sl")),
        current=_num(d.get("current") or d.get("price") or d.get("mark")),
    )


def parse_snapshot(payload: Any) -> Snapshot:
    """Accept a dict (or JSON text). Bad rows are skipped, never fatal."""
    if isinstance(payload, (bytes, str)):
        import json
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("snapshot must be a JSON object")

    warnings: List[str] = []
    raw_acct = payload.get("account") or {}
    if not isinstance(raw_acct, dict):
        raw_acct, warnings = {}, ["account block was not an object"]

    equity = _num(raw_acct.get("equity"))
    if equity is None:
        equity = _num(raw_acct.get("balance"))
    if equity is None:
        equity = 0.0
        warnings.append("no equity supplied; risk percentages will be 0")

    free_margin = _num(raw_acct.get("free_margin"))
    used_margin = _num(raw_acct.get("used_margin"))
    if free_margin is None:
        free_margin = equity - (used_margin or 0.0)
        warnings.append("free_margin missing; derived from equity - used_margin")

    positions, skipped = [], 0
    for row in raw_acct.get("positions") or raw_acct.get("open_positions") or []:
        p = _position_from(row) if isinstance(row, dict) else None
        if p is None:
            skipped += 1
        else:
            positions.append(p)
    if skipped:
        warnings.append("%d unreadable position row(s) skipped" % skipped)

    raw_prop = payload.get("proposal") or payload.get("trade") or {}
    if not isinstance(raw_prop, dict):
        raw_prop = {}
    units = _num(raw_prop.get("units") or raw_prop.get("size"))
    entry = _num(raw_prop.get("entry") or raw_prop.get("entry_price"))
    proposal = Proposal(
        symbol=str(raw_prop.get("symbol") or raw_prop.get("instrument")
                   or "").strip().upper(),
        side=str(raw_prop.get("side") or "long").strip().lower(),
        units=abs(units) if units is not None else 0.0,
        entry=entry or 0.0,
        stop=_num(raw_prop.get("stop") or raw_prop.get("stop_loss")),
        take_profit=_num(raw_prop.get("take_profit") or raw_prop.get("tp")),
        leverage=_num(raw_prop.get("leverage")) or 1.0,
        horizon_days=int(_num(raw_prop.get("horizon_days")) or 1),
    )
    if proposal.side not in ("long", "short", "buy", "sell"):
        proposal.side = "long"
    proposal.side = "long" if proposal.side in ("long", "buy") else "short"

    policy = dict(DEFAULT_POLICY)
    supplied = payload.get("policy")
    if isinstance(supplied, dict):
        for k, v in supplied.items():
            if k == "restricted_symbols":
                policy[k] = [str(s).strip().upper() for s in (v or [])]
            else:
                n = _num(v)
                policy[k] = n if n is not None else v

    corr: Dict[str, Dict[str, float]] = {}
    supplied_corr = payload.get("correlations")
    if isinstance(supplied_corr, dict):
        for a, row in supplied_corr.items():
            if isinstance(row, dict):
                corr[str(a).upper()] = {
                    str(b).upper(): (_num(v) or 0.0) for b, v in row.items()
                }

    return Snapshot(
        account=Account(
            currency=str(raw_acct.get("currency") or "USD").upper(),
            equity=equity,
            free_margin=free_margin,
            used_margin=used_margin or 0.0,
            positions=positions,
        ),
        proposal=proposal,
        policy=policy,
        correlations=corr,
        warnings=warnings,
    )


# ------------------------------------------------------------------- inference

def _ccy(symbol: str) -> Tuple[str, str]:
    """Split 'EURUSD' into ('EUR','USD'); unknown -> ('', '')."""
    s = symbol.replace("/", "").replace("_", "").replace("-", "").upper()
    if len(s) == 6 and s.isalpha():
        return s[:3], s[3:]
    return "", ""


def implied_correlation(a: str, b: str) -> float:
    """Deterministic stand-in when the user supplies no correlation matrix.

    Same base currency (EURUSD vs EURJPY) or same quote currency (EURUSD vs
    GBPUSD) means the two legs move together far more than chance. This is a
    stated approximation, not a measured number - the receipt says so.
    """
    if a == b:
        return 1.0
    ba, qa = _ccy(a)
    bb, qb = _ccy(b)
    if not ba or not bb:
        return 0.0
    if ba == bb or qa == qb:
        return 0.7
    return 0.1


def corr_to(symbol: str, other: str, matrix: Dict[str, Dict[str, float]]) -> float:
    row = matrix.get(symbol) or matrix.get(other) or {}
    if other in row:
        return row[other]
    if symbol in matrix.get(other, {}):
        return matrix[other][symbol]
    return implied_correlation(symbol, other)


# --------------------------------------------------------------------- metrics

def compute_metrics(snap: Snapshot) -> Dict[str, Any]:
    """Flat, addressable fact bundle. Locators are dotted paths."""
    acct, prop, pol = snap.account, snap.proposal, snap.policy
    m: Dict[str, Any] = {}

    m["account.currency"] = acct.currency
    m["account.equity"] = round(acct.equity, 2)
    m["account.free_margin"] = round(acct.free_margin, 2)
    m["account.used_margin"] = round(acct.used_margin, 2)
    m["account.open_positions"] = len(acct.positions)

    m["proposal.symbol"] = prop.symbol
    m["proposal.side"] = prop.side
    m["proposal.units"] = round(prop.units, 2)
    m["proposal.entry"] = round(prop.entry, 6)
    m["proposal.stop"] = round(prop.stop, 6) if prop.stop else None
    m["proposal.take_profit"] = round(prop.take_profit, 6) if prop.take_profit else None
    m["proposal.leverage"] = round(prop.leverage, 2)
    m["proposal.horizon_days"] = prop.horizon_days

    for i, p in enumerate(acct.positions):
        m["positions[%d].symbol" % i] = p.symbol
        m["positions[%d].side" % i] = p.side
        m["positions[%d].units" % i] = round(p.units, 2)
        m["positions[%d].entry" % i] = round(p.entry, 6)
        m["positions[%d].risk_amount" % i] = round(p.risk_amount, 2)
        m["positions[%d].notional" % i] = round(p.notional, 2)

    notional = abs(prop.units) * prop.entry
    stop_distance = abs(prop.entry - prop.stop) if prop.stop else 0.0
    risk_amount = stop_distance * abs(prop.units)
    reward_amount = (abs(prop.take_profit - prop.entry) * abs(prop.units)
                     if prop.take_profit else 0.0)

    m["metrics.notional"] = round(notional, 2)
    m["metrics.stop_distance"] = round(stop_distance, 6)
    m["metrics.risk_amount"] = round(risk_amount, 2)
    m["metrics.reward_amount"] = round(reward_amount, 2)
    m["metrics.risk_pct"] = round(100.0 * risk_amount / acct.equity, 3) if acct.equity else 0.0
    m["metrics.rr_ratio"] = round(reward_amount / risk_amount, 3) if risk_amount else 0.0
    m["metrics.stop_pct_of_price"] = (
        round(100.0 * stop_distance / prop.entry, 3) if prop.entry else 0.0)
    m["metrics.leverage"] = round(prop.leverage, 2)
    m["metrics.effective_leverage"] = (
        round(notional / acct.equity, 3) if acct.equity else 0.0)

    margin_required = notional / prop.leverage if prop.leverage else notional
    m["metrics.margin_required"] = round(margin_required, 2)
    m["metrics.free_margin_after"] = round(acct.free_margin - margin_required, 2)
    m["metrics.free_margin_pct_after"] = (
        round(100.0 * (acct.free_margin - margin_required) / acct.equity, 2)
        if acct.equity else 0.0)

    open_risk = sum(p.risk_amount for p in acct.positions)
    m["metrics.open_risk_amount"] = round(open_risk, 2)
    m["metrics.open_risk_pct"] = (
        round(100.0 * open_risk / acct.equity, 3) if acct.equity else 0.0)
    m["metrics.total_risk_amount"] = round(open_risk + risk_amount, 2)
    m["metrics.total_risk_pct"] = (
        round(100.0 * (open_risk + risk_amount) / acct.equity, 3)
        if acct.equity else 0.0)

    # Exposure is measured in *risk*, not notional: how much of the account
    # disappears if this theme goes against you. Notional/equity is meaningless
    # for leveraged instruments - it is 500% for a perfectly ordinary ticket.
    same_risk = sum(p.risk_amount for p in acct.positions
                    if p.symbol == prop.symbol)
    m["metrics.risk_concentration_pct"] = (
        round(100.0 * (risk_amount + same_risk) / acct.equity, 2)
        if acct.equity else 0.0)

    corr_risk, corr_names = risk_amount, []
    for p in acct.positions:
        if p.symbol == prop.symbol:
            continue
        c = corr_to(prop.symbol, p.symbol, snap.correlations)
        if c >= 0.7:
            corr_risk += p.risk_amount
            corr_names.append("%s(%.2f)" % (p.symbol, c))
    m["metrics.correlated_risk_pct"] = (
        round(100.0 * corr_risk / acct.equity, 2) if acct.equity else 0.0)
    m["metrics.correlated_with"] = corr_names

    m["metrics.worst_case_equity"] = round(acct.equity - open_risk - risk_amount, 2)
    m["metrics.worst_case_drawdown_pct"] = m["metrics.total_risk_pct"]
    m["metrics.positions_after"] = len(acct.positions) + 1
    return m


# ---------------------------------------------------------------------- policy

def _pol(pol: Dict[str, Any], key: str) -> float:
    v = _num(pol.get(key))
    return v if v is not None else _num(DEFAULT_POLICY.get(key)) or 0.0


def policy_check(m: Dict[str, Any], pol: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic rule check. Returns breaches; empty list == clean."""
    out: List[Dict[str, Any]] = []

    def _lookup(loc: str) -> Any:
        if loc.startswith("policy."):
            return pol.get(loc.split(".", 1)[1])
        return m.get(loc)

    def _fmt(v: Any) -> str:
        if isinstance(v, bool):
            return str(v)
        if isinstance(v, (int, float)):
            return "%.2f" % v
        return str(v)

    def breach(rule, detail, locators, severity="hard"):
        out.append({"rule": rule, "severity": severity, "detail": detail,
                    "evidence": [{"source": "policy", "locator": r,
                                  "excerpt": _fmt(_lookup(r))}
                                 for r in locators]})

    restricted = [str(s).upper() for s in (pol.get("restricted_symbols") or [])]
    if m.get("proposal.symbol") in restricted:
        breach("RESTRICTED_SYMBOL",
               "%s is on the restricted list" % m["proposal.symbol"],
               ["policy.restricted_symbols"])

    if m["metrics.risk_pct"] > _pol(pol, "max_risk_pct_per_trade"):
        breach("RISK_PER_TRADE",
               "risk %.2f%% of equity exceeds the %.2f%% cap"
               % (m["metrics.risk_pct"], _pol(pol, "max_risk_pct_per_trade")),
               ["metrics.risk_pct", "policy.max_risk_pct_per_trade"])

    if m["metrics.total_risk_pct"] > _pol(pol, "max_total_risk_pct"):
        breach("TOTAL_RISK",
               "open + proposed risk %.2f%% exceeds the %.2f%% portfolio cap"
               % (m["metrics.total_risk_pct"], _pol(pol, "max_total_risk_pct")),
               ["metrics.total_risk_pct", "policy.max_total_risk_pct"])

    if m["metrics.effective_leverage"] > _pol(pol, "max_leverage"):
        breach("LEVERAGE",
               "effective leverage %.1fx exceeds the %.1fx cap"
               % (m["metrics.effective_leverage"], _pol(pol, "max_leverage")),
               ["metrics.effective_leverage", "policy.max_leverage"])

    if m["metrics.risk_concentration_pct"] > _pol(pol, "max_risk_concentration_pct"):
        breach("RISK_CONCENTRATION",
               "at-risk capital in %s would be %.2f%% of equity, above the "
               "%.2f%% single-name cap"
               % (m["proposal.symbol"], m["metrics.risk_concentration_pct"],
                  _pol(pol, "max_risk_concentration_pct")),
               ["metrics.risk_concentration_pct",
                "policy.max_risk_concentration_pct"])

    if m["metrics.correlated_risk_pct"] > _pol(pol, "max_correlated_risk_pct"):
        breach("CORRELATED_RISK",
               "risk across correlated pairs would be %.2f%%, above the %.2f%% "
               "cap (%s)"
               % (m["metrics.correlated_risk_pct"],
                  _pol(pol, "max_correlated_risk_pct"),
                  ", ".join(m["metrics.correlated_with"]) or "same-currency legs"),
               ["metrics.correlated_risk_pct",
                "policy.max_correlated_risk_pct"])

    if m["metrics.rr_ratio"] and m["metrics.rr_ratio"] < _pol(pol, "min_rr_ratio"):
        breach("REWARD_RISK",
               "reward:risk %.2f is below the %.2f minimum"
               % (m["metrics.rr_ratio"], _pol(pol, "min_rr_ratio")),
               ["metrics.rr_ratio", "policy.min_rr_ratio"])

    if m["metrics.positions_after"] > int(_pol(pol, "max_positions")):
        breach("MAX_POSITIONS",
               "this would be position %d, cap is %d"
               % (m["metrics.positions_after"], int(_pol(pol, "max_positions"))),
               ["metrics.positions_after", "policy.max_positions"])

    if m["metrics.free_margin_pct_after"] < _pol(pol, "min_free_margin_pct"):
        breach("FREE_MARGIN",
               "free margin would fall to %.1f%% of equity, floor is %.1f%%"
               % (m["metrics.free_margin_pct_after"],
                  _pol(pol, "min_free_margin_pct")),
               ["metrics.free_margin_pct_after", "policy.min_free_margin_pct"])

    if m["metrics.stop_pct_of_price"] > _pol(pol, "max_stop_pct_of_price"):
        breach("STOP_TOO_WIDE",
               "stop is %.2f%% away from entry, wider than the %.2f%% limit"
               % (m["metrics.stop_pct_of_price"],
                  _pol(pol, "max_stop_pct_of_price")),
               ["metrics.stop_pct_of_price", "policy.max_stop_pct_of_price"])

    if m["metrics.stop_distance"] == 0:
        breach("NO_STOP",
               "the proposal has no stop; worst case is the whole position",
               ["proposal.stop"], severity="hard")
    return out


def solve_units_for_risk(snap: Snapshot, max_risk_pct: float) -> float:
    """Largest unit size whose stop-loss risk stays inside ``max_risk_pct``."""
    prop, acct = snap.proposal, snap.account
    if not prop.stop or not prop.entry or not acct.equity:
        return 0.0
    distance = abs(prop.entry - prop.stop)
    if distance <= 0:
        return 0.0
    budget = acct.equity * (max_risk_pct / 100.0)
    units = budget / distance
    return float(int(units))          # round down, never up
