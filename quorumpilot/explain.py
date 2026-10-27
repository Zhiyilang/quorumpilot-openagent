"""The "explain why" surface: one proposal in, the whole arbitration out.

Open Agent Track 02 rewards work that shows its reasoning rather than just its
answer. ``python -m quorumpilot explain examples/proposal_risky.json`` runs the
quorum on one proposal and prints the transcript: what each specialist
proposed, the evidence it cited, which claims failed verification and why, how
the tally fell, and what the arbiter did about it. Every number in it is
re-runnable against the raw files - that is the whole point of the track.

render_transcript() is a pure function of the review() result - no I/O, no
clock, no network - so the eval suite asserts on it without a terminal.
"""

from __future__ import annotations

from typing import Any, Dict, List

WIDTH = 72


def _rule(char: str = "-") -> str:
    return char * WIDTH


def _wrap(text: str, indent: str = "  ") -> List[str]:
    lines, cur = [], indent
    for word in str(text).split():
        if len(cur) + len(word) + 1 > WIDTH:
            lines.append(cur.rstrip())
            cur = indent + word + " "
        else:
            cur += word + " "
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def render_transcript(result: Dict[str, Any]) -> str:
    """Render a review() result as a human-readable arbitration transcript."""
    d = result["decision"]
    m = result["metrics"]
    out: List[str] = [
        _rule("="),
        "ARBITRATION TRANSCRIPT",
        _rule("="),
        "",
        "proposal   %s %s %.0f units at %.5f"
        % (d["side"], d["symbol"], m["proposal.units"], m["proposal.entry"]),
        "equity     %.2f %s, %d open position(s)"
        % (m["account.equity"], m["account.currency"],
           m["account.open_positions"]),
        "risk       %.2f%% of equity (%.2f %s)"
        % (d["risk_pct"], d["risk_amount"], m["account.currency"]),
        "",
        "1. WHAT THE SPECIALISTS PROPOSED",
        _rule(),
    ]

    for stance in ("objection", "caution", "support"):
        group = [c for c in result["verified"] if c.get("stance") == stance]
        if not group:
            continue
        out.append("")
        out.append("  [%s] %d claim(s), weight %+d each"
                   % (stance.upper(), len(group), group[0].get("weight", 0)))
        for c in group:
            out.append("    - %s (%s)" % (c.get("id"), c.get("agent")))
            out.extend(_wrap(str(c.get("statement")), indent="        "))
            for ev in (c.get("evidence") or []):
                out.append("        cites %s = %s"
                           % (ev.get("locator"), ev.get("excerpt")))

    out.extend(["", "2. WHAT FAILED VERIFICATION", _rule()])
    if not result["dropped"]:
        out.append("  nothing was dropped")
    for c in result["dropped"]:
        out.append("  - %s (%s)" % (c.get("id"), c.get("agent")))
        out.extend(_wrap(str(c.get("statement")), indent="      "))
        for reason in (c.get("_reasons") or []):
            out.extend(_wrap("reason: " + str(reason), indent="      "))

    t = d["tally"]
    out.extend([
        "",
        "3. THE TALLY",
        _rule(),
        "  support %d   caution %d   objection %d   weighted score %+d"
        % (t["support"], t["caution"], t["objection"], d["score"]),
    ])

    out.extend(["", "4. THE RULING", _rule()])
    if d["breaches"]:
        out.append("  policy breaches:")
        for b in d["breaches"]:
            out.append("    [%s] %s: %s"
                       % (b["severity"], b["rule"], b["detail"]))
    else:
        out.append("  no policy breaches")
    out.append("")
    out.extend(_wrap(d["explain"]))
    for action in d["required_actions"]:
        out.extend(_wrap("- " + str(action)))
    out.extend(["", "  VERDICT: %s" % d["verdict"], "",
                "re-run: python -m quorumpilot explain <proposal.json>",
                _rule("=")])
    return chr(10).join(out)
