"""Receipts: one JSON object and one self-contained HTML page.

Both are self-describing - a judge can read the receipt without the app.
"""

import html
import json
from typing import Any, Dict

_BADGE = {
    "PROCEED": ("#0f9d58", "PROCEED"),
    "PROCEED_WITH_CAUTION": ("#b58900", "PROCEED WITH CAUTION"),
    "REJECT": ("#d13438", "REJECT"),
}
_STANCE = {"support": "#0f9d58", "caution": "#b58900", "objection": "#d13438"}


def build_receipt(result: Dict[str, Any]) -> Dict[str, Any]:
    d = result["decision"]
    r = dict(result["receipt"])
    r["decision"] = {k: d[k] for k in
                     ("verdict", "score", "tally", "claims_total",
                      "claims_verified", "claims_dropped", "dropped",
                      "breaches", "suggested_units", "required_actions",
                      "explain", "symbol", "side", "risk_pct", "risk_amount",
                      "worst_case_equity")}
    r["claims"] = [{"agent": c["agent"], "stance": c["stance"],
                    "statement": c["statement"], "evidence": c["evidence"]}
                   for c in result["verified"]]
    r["metrics"] = result["metrics"]
    return r


def receipt_json(result: Dict[str, Any]) -> str:
    return json.dumps(build_receipt(result), indent=2, ensure_ascii=False)


def _e(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


def render_html(result: Dict[str, Any]) -> str:
    d = result["decision"]
    m = result["metrics"]
    colour, label = _BADGE.get(d["verdict"], ("#555", d["verdict"]))
    cur = m.get("account.currency", "")

    rows = []
    for c in result["verified"]:
        ev = " ".join(
            "<code>%s</code>" % _e(x["locator"]) for x in c["evidence"])
        rows.append(
            "<tr><td><b>%s</b></td>"
            "<td><span style='color:%s'>%s</span></td>"
            "<td>%s</td><td class='ev'>%s</td></tr>"
            % (_e(c["agent"]), _STANCE.get(c["stance"], "#333"),
               _e(c["stance"]), _e(c["statement"]), ev))
    dropped = []
    for c in result["dropped"]:
        dropped.append("<li><b>%s</b> &mdash; %s<br><span class='ev'>dropped: %s"
                       "</span></li>"
                       % (_e(c.get("agent")), _e(c.get("statement")),
                          _e("; ".join(c.get("_reasons") or []))))
    actions = "".join("<li>%s</li>" % _e(a) for a in d["required_actions"])
    breaches = "".join(
        "<li><b>%s</b> &mdash; %s</li>" % (_e(b["rule"]), _e(b["detail"]))
        for b in d["breaches"]) or "<li>none</li>"

    return """<!doctype html><meta charset="utf-8">
<title>QuorumPilot receipt &mdash; %s</title>
<style>
body{font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;
background:#0f1115;color:#e6e6e6}
.wrap{max-width:940px;margin:0 auto;padding:32px 20px 60px}
h1{font-size:22px;margin:0 0 4px}
.badge{display:inline-block;background:%s;color:#fff;padding:6px 14px;
border-radius:999px;font-weight:600;letter-spacing:.4px}
.sub{color:#9aa0a6;margin:8px 0 26px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:12px;margin:20px 0 28px}
.kpi{background:#171a21;border:1px solid #262b36;border-radius:10px;padding:12px}
.kpi span{display:block;color:#9aa0a6;font-size:12px;margin-bottom:4px}
.kpi b{font-size:18px}
h2{font-size:16px;margin:28px 0 10px;border-bottom:1px solid #262b36;
padding-bottom:6px}
table{width:100%%;border-collapse:collapse;font-size:14px}
td,th{padding:8px 10px;border-bottom:1px solid #232833;vertical-align:top;
text-align:left}
th{color:#9aa0a6;font-weight:600}
code{background:#1d2230;padding:1px 5px;border-radius:4px;font-size:12px}
.ev{color:#8b93a1;font-size:12.5px}
ul{margin:8px 0 0 18px;padding:0}
li{margin:5px 0}
footer{margin-top:36px;color:#6b7280;font-size:12px}
</style><div class="wrap">
<h1>QuorumPilot decision receipt</h1>
<div class="sub">%s %s &mdash; reviewed by a 4-agent quorum with a
deterministic evidence verifier.</div>
<p><span class="badge">%s</span></p>
<div class="grid">
<div class="kpi"><span>Cash at risk</span><b>%s %.2f</b></div>
<div class="kpi"><span>Risk / equity</span><b>%.2f%%</b></div>
<div class="kpi"><span>Reward:risk</span><b>%.2f</b></div>
<div class="kpi"><span>Worst-case equity</span><b>%.2f</b></div>
<div class="kpi"><span>Claims verified</span><b>%d / %d</b></div>
<div class="kpi"><span>Suggested size</span><b>%s</b></div>
</div>
<h2>What the quorum said</h2>
<p>%s</p>
<h2>Required actions</h2><ul>%s</ul>
<h2>Rule breaches</h2><ul>%s</ul>
<h2>Verified claims</h2>
<table><tr><th>Agent</th><th>Stance</th><th>Statement</th><th>Evidence</th></tr>
%s</table>
<h2>Claims dropped (could not be proven)</h2>
<ul>%s</ul>
<footer>Brain: %s &middot; duration %d ms &middot; verdict score %d
(objection -4, caution -2, support +1)</footer>
</div>""" % (
        _e(d["symbol"]), colour, _e(d["side"]), _e(d["symbol"]), label,
        _e(cur), d["risk_amount"], d["risk_pct"],
        m.get("metrics.rr_ratio", 0), d["worst_case_equity"],
        d["claims_verified"], d["claims_total"],
        ("%.0f units" % d["suggested_units"]) if d["suggested_units"] else "as proposed",
        _e(d["explain"]), actions, breaches, "".join(rows),
        "".join(dropped) or "<li>none &mdash; every claim cited real evidence</li>",
        _e(result["receipt"]["brain"]), result["receipt"]["duration_ms"],
        d["score"])
