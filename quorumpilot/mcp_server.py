"""Zero-dependency MCP server (JSON-RPC 2.0 over stdio, spec 2025-11-25).

Tools: load_snapshot / review_trade / explain_verdict / policy_check /
suggest_size / ingest_sources. All six share the same deterministic core as
the CLI and the Gradio app - the transport never owns any logic.
"""

import json
import sys
from typing import Any, Dict

from .agent import review
from .arbitrate import suggest_units
from .market import compute_metrics, parse_snapshot, policy_check
from .verify import fact_bundle

PROTOCOL_VERSION = "2025-11-25"
SERVER_INFO = {"name": "quorumpilot", "version": "1.0.0"}

_LAST: Dict[str, Any] = {}


def _tools() -> Dict[str, Any]:
    s = {
        "type": "object",
        "properties": {
            "account": {"type": "object", "description": "equity, margins, positions"},
            "proposal": {"type": "object",
                         "description": "symbol, side, units, entry, stop, tp, leverage"},
            "policy": {"type": "object", "description": "optional risk caps"},
            "correlations": {"type": "object", "description": "optional symbol->symbol->rho"},
        },
    }
    return {
        "load_snapshot": {
            "description": "Parse an account + trade proposal and return the "
                           "computed facts (risk, margin, concentration).",
            "inputSchema": s,
        },
        "review_trade": {
            "description": "Run the full 4-agent quorum: specialize, verify "
                           "every claim, then arbitrate a verdict.",
            "inputSchema": {**s, "required": ["proposal"]},
        },
        "explain_verdict": {
            "description": "Plain-language explanation of the last verdict, "
                           "with the claims that carried it.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        "policy_check": {
            "description": "Run only the deterministic rule engine and return "
                           "breaches.",
            "inputSchema": {**s, "required": ["proposal"]},
        },
        "suggest_size": {
            "description": "Largest position size that would fit inside every "
                           "binding policy cap.",
            "inputSchema": {**s, "required": ["proposal"]},
        },
        "ingest_sources": {
            "description": "Merge a pile of mismatched files (CSVs, JSON, "
                           "different column names) into one book, keep "
                           "provenance, then review the proposal against it.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sources": {
                        "type": "array",
                        "items": {"type": "object",
                                  "properties": {"name": {"type": "string"},
                                                 "text": {"type": "string"}}},
                        "description": "file name + raw contents",
                    },
                    "proposal": {"type": "object"},
                },
                "required": ["sources"],
            },
        },
    }


def _text(payload: Any, limit: int = 12000) -> Dict[str, Any]:
    """Serialise without ever emitting invalid JSON.

    Naive ``[:6000]`` slicing is the classic MCP bug: the client gets a
    half-written string and the whole call dies. If the payload is too big we
    shrink it structurally, and only as a last resort send a pointer to the CLI.
    """
    def dump(p, indent=2):
        return json.dumps(p, ensure_ascii=False, indent=indent)

    s = dump(payload)
    if len(s) > limit:
        s = dump(payload, indent=None)
    if len(s) > limit and isinstance(payload, dict) and "receipt" in payload:
        s = dump({k: v for k, v in payload.items() if k != "receipt"},
                 indent=None)
    if len(s) > limit:
        s = json.dumps({
            "truncated": True,
            "note": "response exceeded the MCP text limit; run "
                    "`python -m quorumpilot review --json` for the full receipt",
            "verdict": (payload.get("decision") or {}).get("verdict"),
        }, ensure_ascii=False)
    return {"content": [{"type": "text", "text": s}], "isError": False}


def call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "load_snapshot":
        snap = parse_snapshot(args)
        m = compute_metrics(snap)
        _LAST["snapshot"], _LAST["metrics"] = snap, m
        return {"facts": {k: m[k] for k in sorted(m) if not k.startswith("positions")},
                "warnings": snap.warnings}

    if name == "policy_check":
        snap = parse_snapshot(args)
        m = compute_metrics(snap)
        return {"breaches": policy_check(m, snap.policy),
                "policy": snap.policy}

    if name == "suggest_size":
        snap = parse_snapshot(args)
        m = compute_metrics(snap)
        b = policy_check(m, snap.policy)
        return {"proposed_units": m["proposal.units"],
                "suggested_units": suggest_units(snap, m, b),
                "breaches": [x["rule"] for x in b]}

    if name == "review_trade":
        result = review(args)
        _LAST["result"] = result
        d = result["decision"]
        return {
            "verdict": d["verdict"],
            "score": d["score"],
            "tally": d["tally"],
            "symbol": d["symbol"],
            "side": d["side"],
            "risk_pct": d["risk_pct"],
            "risk_amount": d["risk_amount"],
            "suggested_units": d["suggested_units"],
            "required_actions": d["required_actions"],
            "breaches": [{"rule": b["rule"], "detail": b["detail"]}
                         for b in d["breaches"]],
            "explain": d["explain"],
            "verified_claims": [{"agent": c["agent"], "stance": c["stance"],
                                 "statement": c["statement"]}
                                for c in result["verified"][:12]],
            "dropped": d["dropped"],
            "receipt": result["receipt"],
        }

    if name == "ingest_sources":
        from .ingest import Blob, ingest, render_ingest_report
        blobs = [Blob(str(s.get("name") or "source-%d" % (i + 1)),
                      str(s.get("text") or ""))
                 for i, s in enumerate(args.get("sources") or [])]
        ing = ingest(blobs, proposal=args.get("proposal"))
        out = {
            "report": render_ingest_report(ing),
            "positions": len(ing.payload["account"]["positions"]),
            "conflicts": ing.conflicts,
            "warnings": ing.warnings,
            "provenance": ing.provenance,
            "payload": ing.payload,
        }
        if ing.payload.get("proposal", {}).get("symbol"):
            result = review(ing.payload)
            _LAST["result"] = result
            out["verdict"] = result["decision"]["verdict"]
            out["explain"] = result["decision"]["explain"]
            out["breaches"] = [b["rule"] for b in result["decision"]["breaches"]]
            out["suggested_units"] = result["decision"]["suggested_units"]
        return out

    if name == "explain_verdict":
        result = _LAST.get("result")
        if result is None:
            return {"error": "run review_trade first"}
        return {"explain": result["decision"]["explain"],
                "verdict": result["decision"]["verdict"],
                "claims": [{"agent": c["agent"], "stance": c["stance"],
                            "statement": c["statement"]}
                           for c in result["verified"]]}

    raise ValueError("unknown tool: %s" % name)


def handle(msg: Dict[str, Any]) -> Dict[str, Any]:
    method = msg.get("method")
    rid = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid,
                "result": {"protocolVersion": msg.get("params", {})
                           .get("protocolVersion", PROTOCOL_VERSION),
                           "capabilities": {"tools": {}},
                           "serverInfo": SERVER_INFO}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid,
                "result": {"tools": [{"name": k, **v}
                                     for k, v in _tools().items()]}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        try:
            return {"jsonrpc": "2.0", "id": rid,
                    "result": _text(call_tool(name, params.get("arguments") or {}))}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text",
                                            "text": "error: %s" % exc}],
                               "isError": True}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if rid is None:
        return {}
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": "method not found: %s" % method}}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
