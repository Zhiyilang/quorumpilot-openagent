"""Evidence verifier - the part of the system that is allowed to say "no".

An agent (LLM or rule-based) may *propose* any claim it likes. A claim only
survives into the verdict if every piece of evidence it cites

  1. resolves to a field that actually exists in the fact bundle, and
  2. the number or string quoted in the excerpt really is the value there.

Unprovable claims are dropped and listed in the receipt with a reason. This
is what makes the quorum safe to plug an LLM into: hallucinated numbers cost
the model its vote, they do not cost the user their money.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def fact_bundle(snapshot, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Metrics plus policy values, all addressable with dotted locators."""
    bundle = dict(metrics)
    for k, v in (snapshot.policy or {}).items():
        bundle["policy." + k] = v
    bundle["account.currency"] = snapshot.account.currency
    return bundle


def resolve(bundle: Dict[str, Any], locator: str) -> Tuple[bool, Any]:
    if locator in bundle:
        return True, bundle[locator]
    # tolerant lookup: 'metrics.risk_pct' -> 'risk_pct'
    tail = locator.split(".")[-1]
    if tail in bundle:
        return True, bundle[tail]
    # 'positions[0].symbol' with a different index but the same field
    m = re.match(r"^positions\[\d+\]\.(.+)$", locator)
    if m:
        for k, v in bundle.items():
            if k.startswith("positions[") and k.endswith("." + m.group(1)):
                return True, v
    return False, None


def _numbers(text: str) -> List[float]:
    return [float(x) for x in _NUMBER.findall(text or "")]


def _excerpt_matches(value: Any, excerpt: str, tol: float = 0.02) -> bool:
    if excerpt is None:
        return False
    text = str(excerpt)
    if isinstance(value, bool):
        return str(value).lower() in text.lower()
    if isinstance(value, (int, float)):
        nums = _numbers(text)
        if not nums:
            return False
        target = float(value)
        return any(abs(n - target) <= max(tol, abs(target) * 0.01) for n in nums)
    s = str(value)
    if not s:
        return False
    return s.lower() in text.lower()


def verify_claim(claim: Dict[str, Any],
                 bundle: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Return (survives, reasons)."""
    reasons: List[str] = []
    evidence = claim.get("evidence") or []
    if not evidence:
        return False, ["no evidence attached"]
    if not str(claim.get("statement") or "").strip():
        return False, ["empty statement"]
    if claim.get("stance") not in ("support", "caution", "objection"):
        return False, ["unknown stance %r" % claim.get("stance")]
    for ev in evidence:
        locator = str(ev.get("locator") or "")
        found, value = resolve(bundle, locator)
        if not found:
            reasons.append("locator %r not found" % locator)
            continue
        if not _excerpt_matches(value, str(ev.get("excerpt") or "")):
            reasons.append("excerpt %r does not match %s=%r"
                           % (str(ev.get("excerpt"))[:40], locator, value))
    return (not reasons), reasons


def verify_claims(claims: List[Dict[str, Any]],
                  bundle: Dict[str, Any]) -> Tuple[List[Dict[str, Any]],
                                                   List[Dict[str, Any]]]:
    """Split claims into (verified, dropped). Dropped carry ``_reasons``."""
    verified, dropped = [], []
    for c in claims:
        ok, reasons = verify_claim(c, bundle)
        if ok:
            verified.append(c)
        else:
            d = dict(c)
            d["_reasons"] = reasons
            dropped.append(d)
    return verified, dropped


def locate(bundle: Dict[str, Any], locator: str) -> Optional[Any]:
    ok, v = resolve(bundle, locator)
    return v if ok else None
