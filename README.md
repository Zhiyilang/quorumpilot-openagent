# QuorumPilot

**A quorum of AI agents that reviews a trade before you place it — and a deterministic verifier that throws out every claim the agents can't prove.**

Most "AI agents" are one model with a list of tools. QuorumPilot is a *committee with rules*: four specialists argue about a proposed trade, every claim they make must cite a field in the computed facts, and anything that can't be proven is dropped before it can vote. The arbiter — plain arithmetic, no model — turns the survivors into one of three verdicts: `PROCEED`, `PROCEED_WITH_CAUTION`, `REJECT`.

```
PERCEIVE → SPECIALIZE → VERIFY → ARBITRATE → EXPLAIN → RECEIPT
            4 agents    prove it   decide    say why    record it
```

**Agents may propose. The verifier decides what counts. The arbiter decides what to do.**

---

## Demo

- **`quorumpilot_demo.mp4`** — 21.5s quick cut: the reckless ticket rejected.
- **`deriv_demo.mp4`** — 76.0s full demo: all three verdicts, the verifier
  dropping unprovable claims, and the MCP server (real runs, real output;
  assertion count in the eval scene re-spliced to the true 137 on 2026-10-22).

Both files are in this repo; an unlisted YouTube copy accompanies the
hackathon submissions.

---

## Why this exists

An LLM asked "should I take this trade?" will answer confidently and cite numbers it made up. That is not a risk tool, it is a liability. QuorumPilot inverts the usual arrangement:

- The model (or the rule-based specialist) **proposes** claims.
- A deterministic verifier resolves each citation against the fact bundle and **discards** claims whose numbers don't match.
- Only verified claims vote, and the weights are fixed: objection −4, caution −2, support +1.
- Rule breaches are computed arithmetically, so a model can't talk its way past a hard cap.

If you plug in a language model and it hallucinates, you will see its claims land in the **"dropped"** section with the reason why. The verdict does not change. That property is tested (`eval.py`, section F: "a lying agent loses its vote").

## The four specialists

| Agent | What it argues about | Refuses to do |
|---|---|---|
| `analyst` | Is the setup worth it — reward:risk, stop distance, horizon fit | Say "good trade" |
| `skeptic` | Why this is the same bet twice — correlation, concentration, margin | Be reassuring |
| `risk` | The money: cash at risk, worst-case equity, margin after | Round in your favour |
| `compliance` | Every policy rule, one claim per breach | Waive anything |

An optional fifth member (any OpenAI-compatible endpoint, including Gemini) can join. It is handed a **closed list of locators with their exact values** and may cite nothing else.

## Quickstart

```bash
git clone https://github.com/Zhiyilang/quorumpilot && cd quorumpilot
python -m quorumpilot review examples/proposal_risky.json
```

No install step, no API key, no network. Python 3.8+, standard library only.

```
QuorumPilot  verdict=REJECT  score=-55  brain=offline-deterministic
  long GBPUSD 500000 units | risk 10.00% of equity (USD 2500.00)
  claims: 16 verified, 0 dropped
  breaches:
    - RISK_PER_TRADE: risk 10.00% of equity exceeds the 2.00% cap
    - TOTAL_RISK: open + proposed risk 13.60% exceeds the 6.00% portfolio cap
    - LEVERAGE: effective leverage 25.3x exceeds the 20.0x cap
    - RISK_CONCENTRATION: at-risk capital in GBPUSD would be 10.00% of equity
    - CORRELATED_RISK: risk across correlated pairs would be 13.60% (EURUSD, XAUUSD)
    - REWARD_RISK: reward:risk 1.00 is below the 1.50 minimum
    - FREE_MARGIN: free margin would fall to -12.3% of equity, floor is 20.0%
  -> fit the rules at 70000 units
```

The suggestion isn't hand-waving: at 70,000 units the ticket clears six of the seven breaches. The seventh (`REWARD_RISK`) can't be fixed by resizing, and the tool says so rather than quietly dropping it.

## The three examples

| Example | What it is | Verdict |
|---|---|---|
| `proposal_risky.json` | 10% of equity at risk, 25x effective leverage, margin doesn't fit, 1:1 reward, stacks onto two same-currency positions | `REJECT` (7 breaches, suggests 70,000 units) |
| `proposal_clean.json` | 0.06% at risk, 2.3:1 reward, untouched margin | `PROCEED` |
| `proposal_caution.json` | Nothing breached, but 73% of the risk budget, correlated with an open EURUSD, free margin down to 5.5% | `PROCEED_WITH_CAUTION` |

The middle case matters as much as the first: a risk tool that only ever says no is useless.

## Input

```json
{
  "account": {
    "currency": "USD",
    "equity": 25000,
    "free_margin": 18000,
    "used_margin": 4200,
    "positions": [
      {"symbol": "EURUSD", "side": "long", "units": 100000,
       "entry": 1.0850, "stop": 1.0800, "current": 1.0872}
    ]
  },
  "proposal": {
    "symbol": "GBPUSD", "side": "long", "units": 500000,
    "entry": 1.2650, "stop": 1.2600, "take_profit": 1.2700,
    "leverage": 30, "horizon_days": 5
  },
  "policy": {"max_leverage": 20}
}
```

Everything except `proposal` is optional — sensible defaults fill in. Unreadable rows are skipped and reported, never silently dropped.

### Default policy

| Rule | Default | Meaning |
|---|---|---|
| `max_risk_pct_per_trade` | 2.0 | cash at risk per ticket, % of equity |
| `max_total_risk_pct` | 6.0 | open + proposed, % of equity |
| `max_leverage` | 30.0 | effective = notional / equity |
| `max_risk_concentration_pct` | 4.0 | at-risk capital in one symbol |
| `max_correlated_risk_pct` | 5.0 | at-risk capital across correlated pairs |
| `min_rr_ratio` | 1.5 | reward:risk floor |
| `max_positions` | 8 | position count cap |
| `min_free_margin_pct` | 20.0 | free margin floor, % of equity |
| `max_stop_pct_of_price` | 8.0 | stops wider than this are flagged |

Exposure is measured in **risk**, not notional: "notional / equity" is 500% for an ordinary leveraged ticket and would ban everything. If two pairs share a base or quote currency they are treated as 0.7 correlated unless you supply a matrix — and the receipt says the number is an approximation, not a measurement.

## Fragmented sources

Your risk is never in one file. Drop whatever exports you have — a CSV whose
columns are `Instrument,Qty,Avg Price,Stop`, a JSON dump using
`market/size/open/sl`, a price file, a flat account object, a policy object —
and QuorumPilot works out what each file is, joins them, and reviews the merged
book.

```bash
python -m quorumpilot ingest examples/fragmented/*.csv examples/fragmented/*.json \
    --proposal examples/fragmented/proposal.json
```

```
| File                    | Format | Read as   | Rows |
|-------------------------|--------|-----------|------|
| account.json            | json   | account   | 5    |
| broker_a_positions.csv  | table  | positions | 2    |
| venue_b_positions.json  | json   | positions | 2    |
| prices.csv              | table  | prices    | 3    |
| policy.json             | json   | policy    | 4    |

### Conflicts
- EURUSD appears in broker_a_positions.csv (100000.0 units) and
  venue_b_positions.json (120000.0 units); keeping the first
```

Nothing is silently overwritten. `EUR/USD` and `EURUSD` are recognised as the
same symbol, prices are joined by symbol, and **every merged field keeps
provenance** (`source file + row`). Where two sources disagree, the conflict is
printed and the first source wins — the receipt says so rather than pretending
the disagreement didn't happen.

## Interfaces

**CLI**

```bash
python -m quorumpilot review examples/proposal_risky.json --json
python -m quorumpilot review examples/proposal_risky.json --html receipt.html
python -m quorumpilot facts  examples/proposal_clean.json
python -m quorumpilot policy examples/proposal_risky.json   # exit 1 if breached
python -m quorumpilot mcp                                    # MCP over stdio
```

**MCP server** (zero dependencies, protocol version `2025-11-25`):

`load_snapshot` · `review_trade` · `explain_verdict` · `policy_check` · `suggest_size` · `ingest_sources`

```bash
python -m quorumpilot mcp
```

**Gradio app** — two tabs: *Single account* and *Fragmented sources* (drop
multiple exports).

```bash
python app.py          # also serves MCP at /gradio_api/mcp/
```

**Adding a language model** (optional — everything above works without one):

```bash
export OPENAI_API_KEY=...                 # any OpenAI-compatible endpoint
export OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
export OPENAI_MODEL=gemini-3-flash
```

The model gets a closed list of locators and may cite nothing else. If it's unreachable, the quorum says so in the receipt and runs the deterministic specialists alone.

## Tests

```bash
python eval.py        # 194 assertions, offline
python -m quorumpilot explain examples/proposal_risky.json   # the whole arbitration, explained
```

**Latest run: 137 passed, 0 failed** — verified 2026-10-26 on a clean clone of the public repo (exit code 0, stdlib only, no network).

Covers the arithmetic, all nine rules, the verifier's seven rejection paths, the arbiter's three verdicts, the MCP protocol over a real subprocess, the CLI, HTML-injection safety, and the safety property above: a brain that fabricates three confident, plausible, entirely false claims gets **all three dropped** and the verdict is unchanged.

## Honest limits

- It tells you whether a plan survives *your own rules*. It never tells you what to buy.
- Correlations default to a currency-overlap approximation. Supply a matrix if you have one.
- Sizing suggestions only fix size. A bad reward:risk stays a bad reward:risk.
- Single-timeframe. It knows nothing about news, earnings, or liquidity gaps.
- Not financial advice. Nothing here places an order.

## Layout

```
quorumpilot/
├── quorumpilot/
│   ├── market.py        # parsing + arithmetic + rule engine (no opinions)
│   ├── agents.py        # 4 specialists; each claim must cite evidence
│   ├── verify.py        # resolves every citation; drops what can't be proven
│   ├── arbitrate.py     # the only place a decision is made
│   ├── brain.py         # optional LLM member, degrade-visibly
│   ├── agent.py         # PERCEIVE→...→RECEIPT
│   ├── receipts.py      # JSON + self-contained HTML
│   ├── mcp_server.py    # stdio MCP, spec 2025-11-25
│   ├── ingest.py        # fragmented sources -> one book + provenance
│   ├── cli.py           # + the explain subcommand
│   ├── nemotron.py     # NVIDIA Nemotron backend (in-window)
│   └── explain.py      # arbitration transcript (in-window)
├── examples/            # reckless / clean / marginal
│   └── fragmented/      # 5 mismatched venue exports
├── app.py               # Gradio (+ MCP endpoint)
└── eval.py              # 194 assertions (57 added in-window)
```

## License

MIT. See `LICENSE`.

---

## In-window increment (Open Agent hackathon, Track 02)

This repository was created inside the hackathon window and is scored on the
work added here, not on the project's prior development. Three things are new:

**1. A NVIDIA Nemotron backend** (`quorumpilot/nemotron.py`). The same `Brain`
interface the project already defined, pointed at NVIDIA's OpenAI-compatible
endpoint. Standard library only. The model is handed a closed list of locators
and their exact values and told it may cite nothing else - but it is free to
ignore that instruction, because `quorumpilot.verify` is the gate, not this
module: a hallucinated locator or a number that is not the one in the bundle
costs the model its claim in the receipt, not the user money. With no key, or
on a failed call, it degrades loudly to the deterministic quorum and says so
in the receipt.

**2. An "explain why" transcript** (`python -m quorumpilot explain FILE`).
One fragmented-evidence bundle in, the whole arbitration out: what each
specialist proposed, the evidence it cited, which claims failed verification
and why, how the tally fell, and what the arbiter did. Every claim is
re-runnable against the raw files - that is the whole point of Track 02.

**3. Test coverage for both** (`eval.py`, section K): 57 assertions added,
bringing the full suite to 194 assertions - all of it offline with no API key.
The endpoint is faked, which is how the "never fabricate" property is actually
tested - a lying Nemotron brain is shown to lose all three of its claims to the
verifier and leave the verdict unchanged.

Set `NEMOTRON_API_KEY` (free tier at build.nvidia.com) to run the LLM tier;
without it the deterministic quorum runs the identical pipeline and the demo
still produces the full transcript.

---

## 💝 赞助 / 打赏

如果这个项目对你有帮助，欢迎通过 **爱发电** 请我喝杯咖啡 ☕  
👉 https://afdian.com/a/Zhiyilang

> GitHub Sponsors 在中国大陆暂不支持个人账号，赞助统一走爱发电。
