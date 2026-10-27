"""Gradio app for QuorumPilot.

Same core as the CLI and the MCP server - this file only renders. It also
exposes the quorum over MCP at /gradio_api/mcp/ (launch(mcp_server=True)).
"""

import json
import os
import tempfile
from pathlib import Path

import gradio as gr

from quorumpilot.agent import review
from quorumpilot.market import compute_metrics, parse_snapshot
from quorumpilot.receipts import receipt_json, render_html

ROOT = Path(__file__).resolve().parent
EX = ROOT / "examples"

CSS = """
.big {font-size:20px;font-weight:700}
.ok {color:#0f9d58;font-weight:700}
.warn {color:#b58900;font-weight:700}
.bad {color:#d13438;font-weight:700}
"""

_DEMOS = {
    "Reckless (7 rules breached)": "proposal_risky.json",
    "Clean (should clear)": "proposal_clean.json",
    "Marginal (clears with caution)": "proposal_caution.json",
}


def load_demo(name: str) -> str:
    f = EX / _DEMOS.get(name, "proposal_risky.json")
    return f.read_text(encoding="utf-8")


def _verdict_md(d: dict) -> str:
    cls = {"PROCEED": "ok", "PROCEED_WITH_CAUTION": "warn",
           "REJECT": "bad"}.get(d["verdict"], "")
    size = ("<b>%s</b>" % d["suggested_units"]) if d["suggested_units"] else "as proposed"
    lines = [
        '<div class="big %s">%s</div>' % (cls, d["verdict"].replace("_", " ")),
        "",
        "**%s %s** &middot; risk **%.2f%%** of equity "
        "(%s %.2f) &middot; worst-case equity **%.2f**"
        % (d["side"], d["symbol"], d["risk_pct"], "USD", d["risk_amount"],
           d["worst_case_equity"]),
        "",
        "Claims: **%d verified**, %d dropped &middot; score **%d** "
        "(objection -4, caution -2, support +1)"
        % (d["claims_verified"], d["claims_dropped"], d["score"]),
        "",
        "Suggested size: %s" % size,
        "",
        d["explain"],
    ]
    if d["required_actions"]:
        lines += ["", "### Required actions"] + ["- " + a
                                                 for a in d["required_actions"]]
    return "\n".join(lines)


def _claims_md(claims) -> str:
    if not claims:
        return "_no claims_"
    icon = {"support": "OK", "caution": "CAUTION", "objection": "OBJECTION"}
    rows = ["| Agent | Stance | Statement | Evidence |", "|---|---|---|---|"]
    for c in claims:
        ev = ", ".join("`%s`" % e["locator"] for e in c["evidence"])
        rows.append("| %s | %s | %s | %s |"
                    % (c["agent"], icon.get(c["stance"], c["stance"]),
                       c["statement"].replace("|", "/"), ev))
    return "\n".join(rows)


def run_quorum(payload: str):
    try:
        parsed = json.loads(payload)
    except Exception as exc:
        msg = "Could not read the JSON: %s" % exc
        return (msg, "", "", "", {}, [], None)
    result = review(parsed, prefer_llm=False)
    d = result["decision"]
    m = result["metrics"]

    facts = {k: m[k] for k in sorted(m)
             if k.startswith(("metrics.", "account.", "proposal."))}
    dropped_md = ("_nothing was dropped - every claim cited evidence that "
                  "resolved_" if not result["dropped"] else "\n".join(
                      "- **%s** (%s): %s  \n  _dropped: %s_"
                      % (c.get("agent"), c.get("id"), c.get("statement"),
                         "; ".join(c.get("_reasons") or []))
                      for c in result["dropped"]))
    trace = [[s["stage"], s["detail"]] for s in result["receipt"]["trace"]]
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(render_html(result))
        report = fh.name
    return (_verdict_md(d), _claims_md(result["verified"]), dropped_md,
            json.dumps(facts, indent=2), json.loads(receipt_json(result)),
            trace, report)


FRAG_FILES = sorted(str(p) for p in (EX / "fragmented").glob("*")
                    if p.suffix != ".json" or p.name != "proposal.json")
FRAG_PROPOSAL = (EX / "fragmented" / "proposal.json").read_text(encoding="utf-8")


def run_fragmented(files, proposal_text):
    """Drop in a pile of mismatched exports; merge, then review."""
    from quorumpilot.ingest import Blob, ingest, render_ingest_report
    if not files:
        return ("Drop at least one CSV or JSON export.", "", "")
    paths = files if isinstance(files, list) else [files]
    try:
        prop = json.loads(proposal_text) if proposal_text.strip() else None
    except Exception as exc:
        return ("Could not read the proposal JSON: %s" % exc, "", "")
    blobs = []
    for p in paths:
        path = Path(p if isinstance(p, str) else getattr(p, "name", ""))
        try:
            blobs.append(Blob(path.name, path.read_text(encoding="utf-8",
                                                        errors="replace")))
        except OSError as exc:
            return ("Could not read %s: %s" % (path.name, exc), "", "")
    ing = ingest(blobs, proposal=prop)
    report = render_ingest_report(ing)
    if not ing.payload.get("proposal", {}).get("symbol"):
        return (report, "_no proposal supplied - facts only_", "")
    result = review(ing.payload, prefer_llm=False)
    return (report, _verdict_md(result["decision"]),
            _claims_md(result["verified"]))


def build():
    with gr.Blocks(title="QuorumPilot", css=CSS) as demo:
        gr.Markdown(
            "# QuorumPilot\n"
            "A **quorum of four specialist agents** reviews a trade before you "
            "place it. Every claim must cite a field in the computed facts, a "
            "deterministic verifier throws out anything it cannot prove, and "
            "only what survives gets a vote.\n\n"
            "**Agents may propose. The verifier decides what counts. "
            "The arbiter decides what to do.**")
        with gr.Tabs():
            with gr.Tab("Single account"):
                with gr.Row():
                    with gr.Column(scale=1):
                        demo_choice = gr.Dropdown(
                            list(_DEMOS), value=list(_DEMOS)[0], label="Example")
                        payload = gr.Textbox(
                            label="Account + proposal (JSON)", lines=18,
                            value=load_demo(list(_DEMOS)[0]))
                        btn = gr.Button("Run the quorum", variant="primary")
                    with gr.Column(scale=2):
                        verdict = gr.Markdown()
                        with gr.Accordion(
                                "Verified claims (what the agents said)",
                                open=True):
                            claims = gr.Markdown()
                        with gr.Accordion(
                                "Dropped claims (could not be proven)",
                                open=False):
                            dropped = gr.Markdown()
                        with gr.Accordion("Computed facts", open=False):
                            facts = gr.Code(language="json", label="")
                        with gr.Accordion("Decision receipt (JSON)", open=False):
                            receipt = gr.JSON(label="")
                        with gr.Accordion("Trace", open=False):
                            trace = gr.Dataframe(headers=["stage", "detail"],
                                                 label="", wrap=True)
                        report = gr.File(label="Download HTML receipt")
            with gr.Tab("Fragmented sources"):
                gr.Markdown(
                    "Your book is never in one file. Drop whatever exports you "
                    "have - different column names, different date formats, "
                    "CSV next to JSON. QuorumPilot works out what each file is, "
                    "joins them, keeps **provenance** for every merged field, "
                    "and reports any place where two sources disagree instead "
                    "of quietly picking one.")
                with gr.Row():
                    with gr.Column(scale=1):
                        files = gr.File(file_count="multiple",
                                        label="Venue exports (CSV / JSON)",
                                        value=FRAG_FILES)
                        frag_prop = gr.Textbox(label="Proposal (JSON)", lines=8,
                                               value=FRAG_PROPOSAL)
                        btn2 = gr.Button("Ingest and review", variant="primary")
                    with gr.Column(scale=2):
                        frag_report = gr.Markdown()
                        frag_verdict = gr.Markdown()
                        with gr.Accordion("Verified claims", open=True):
                            frag_claims = gr.Markdown()
                btn2.click(run_fragmented, inputs=[files, frag_prop],
                           outputs=[frag_report, frag_verdict, frag_claims])
        demo_choice.change(load_demo, inputs=demo_choice, outputs=payload)
        btn.click(run_quorum, inputs=payload,
                  outputs=[verdict, claims, dropped, facts, receipt, trace,
                           report])
        gr.Markdown(
            "---\n"
            "No API key is needed: the four specialists are deterministic. "
            "Set `OPENAI_API_KEY` to add a fifth, LLM member - it is handed a "
            "closed list of locators and may cite nothing else, so anything it "
            "invents is dropped in the section above.")
    return demo


if __name__ == "__main__":
    build().launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
        css=CSS,
        mcp_server=True,
        show_api=False,
    )
