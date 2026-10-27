"""Command line surface. Same core as the MCP server and the Gradio app."""

import argparse
import json
import sys
from pathlib import Path

from .agent import review
from .market import (compute_metrics, parse_snapshot, policy_check,
                     solve_units_for_risk)
from .receipts import receipt_json, render_html

EXAMPLE = Path(__file__).resolve().parent.parent / "examples"


def _load(src: str) -> str:
    p = Path(src)
    return p.read_text(encoding="utf-8") if p.exists() else src


def cmd_review(args) -> int:
    result = review(_load(args.input), prefer_llm=not args.offline)
    d = result["decision"]
    if args.json:
        print(receipt_json(result))
        return 0
    print("QuorumPilot  verdict=%s  score=%d  brain=%s"
          % (d["verdict"], d["score"], result["receipt"]["brain"]))
    print("  %s %s %.0f units | risk %.2f%% of equity (%s %.2f)"
          % (d["side"], d["symbol"], result["metrics"]["proposal.units"],
             d["risk_pct"], result["metrics"]["account.currency"],
             d["risk_amount"]))
    print("  claims: %d verified, %d dropped"
          % (d["claims_verified"], d["claims_dropped"]))
    if d["breaches"]:
        print("  breaches:")
        for b in d["breaches"]:
            print("    - %s: %s" % (b["rule"], b["detail"]))
    print("  %s" % d["explain"])
    if d["suggested_units"]:
        print("  -> fit the rules at %.0f units" % d["suggested_units"])
    for s in result["receipt"]["trace"]:
        print("  [%s] %s" % (s["stage"], s["detail"]))
    if args.html:
        Path(args.html).write_text(render_html(result), encoding="utf-8")
        print("HTML receipt written to %s" % args.html, file=sys.stderr)
    return 0


def cmd_facts(args) -> int:
    snap = parse_snapshot(_load(args.input))
    m = compute_metrics(snap)
    for k in sorted(m):
        print("%-34s %s" % (k, m[k]))
    return 0


def cmd_policy(args) -> int:
    snap = parse_snapshot(_load(args.input))
    m = compute_metrics(snap)
    b = policy_check(m, snap.policy)
    if not b:
        print("no breaches")
        return 0
    for x in b:
        print("[%s] %s" % (x["rule"], x["detail"]))
    return 1


def cmd_ingest(args) -> int:
    """Merge a pile of mismatched files, then run the quorum on the result."""
    from .ingest import ingest_files, render_ingest_report
    proposal = None
    if args.proposal:
        proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
    ing = ingest_files(args.files, proposal=proposal)
    print(render_ingest_report(ing))
    if args.json:
        print(json.dumps({"payload": ing.payload,
                          "conflicts": ing.conflicts,
                          "warnings": ing.warnings}, indent=2))
        return 0
    if not ing.payload.get("proposal", {}).get("symbol"):
        print("\nNo proposal found (pass --proposal FILE); facts only.")
        return 0
    result = review(ing.payload, prefer_llm=not args.offline)
    d = result["decision"]
    print("\nQuorumPilot  verdict=%s  score=%d" % (d["verdict"], d["score"]))
    print("  %s" % d["explain"])
    if d["suggested_units"]:
        print("  -> fit the rules at %.0f units" % d["suggested_units"])
    return 0


def cmd_explain(args) -> int:
    """Print the arbitration transcript: who claimed what, and why it held."""
    from .explain import render_transcript
    result = review(_load(args.input), prefer_llm=not args.offline)
    print(render_transcript(result))
    if args.json:
        print(receipt_json(result))
    return 0


def cmd_mcp(_args) -> int:
    from .mcp_server import main
    return main()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="quorumpilot",
        description="4-agent quorum with a deterministic evidence verifier")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("review", help="run the quorum on a proposal")
    p.add_argument("input", nargs="?", default=str(EXAMPLE / "proposal_risky.json"))
    p.add_argument("--json", action="store_true")
    p.add_argument("--html")
    p.add_argument("--offline", action="store_true",
                   help="ignore any configured LLM")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("facts", help="print the computed fact bundle")
    p.add_argument("input", nargs="?", default=str(EXAMPLE / "proposal_risky.json"))
    p.set_defaults(func=cmd_facts)

    p = sub.add_parser("policy", help="rule engine only")
    p.add_argument("input", nargs="?", default=str(EXAMPLE / "proposal_risky.json"))
    p.set_defaults(func=cmd_policy)

    p = sub.add_parser("ingest", help="merge fragmented sources, then review")
    p.add_argument("files", nargs="+",
                   help="CSVs / JSON blobs from whichever venues")
    p.add_argument("--proposal")
    p.add_argument("--json", action="store_true")
    p.add_argument("--offline", action="store_true")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("explain", help="print the arbitration transcript")
    p.add_argument("input", nargs="?",
                   default=str(EXAMPLE / "proposal_risky.json"))
    p.add_argument("--json", action="store_true",
                   help="also print the receipt JSON")
    p.add_argument("--offline", action="store_true",
                   help="ignore any configured LLM")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("mcp", help="run the MCP server over stdio")
    p.set_defaults(func=cmd_mcp)

    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    return args.func(args)
