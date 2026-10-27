# Demo script — 2:55

Target: under 3 minutes, English, screen recording with a terminal and a browser. No slide intro; open on the tool.

## 0:00 — The problem, in one sentence (15s)

> "Ask a language model whether a trade is safe and it will answer confidently — with numbers it made up. So I built a committee where a model is allowed to speak, but not allowed to be believed."

## 0:15 — The reckless ticket (40s)

Terminal:

```bash
python -m quorumpilot review examples/proposal_risky.json
```

Narrate the output as it appears:

- `verdict=REJECT`, `score=-55`
- 10% of equity at risk — 5x the 2% cap
- 25x effective leverage against a 20x cap
- reward:risk 1.00 against a 1.50 floor
- seven breaches listed with their numbers
- **pause here**: "and it doesn't just say no — at 70,000 units this clears six of the seven"

## 0:55 — Show it's not just a "no" machine (30s)

```bash
python -m quorumpilot review examples/proposal_clean.json
python -m quorumpilot review examples/proposal_caution.json
```

- clean → `PROCEED`
- marginal → `PROCEED_WITH_CAUTION`, with the three reasons (correlated with an open EURUSD, 73% of the risk budget, free margin down to 5.5%)

> "Three verdicts, and the middle one is the point: a risk tool that only ever says no gets turned off."

## 1:25 — The part that matters: proving the claims (40s)

Open the Gradio app (`python app.py`) on the reckless example.

- "Verified claims" tab: each row is an agent, a stance, and the fields it cited.
- "Dropped claims" tab — **run this live**: set `OPENAI_API_KEY` to a bogus value first so you can show the degrade path, or use the eval section.

Best version of this beat — paste into a terminal:

```bash
python eval.py    # scroll to section F
```

```
F. a lying agent loses its vote
  ok   the liar's claims are all dropped
  ok   the liar's claims never reach the verdict
  ok   the verdict is unchanged by the liar
```

> "That test hands the quorum a brain that fabricates three confident, plausible, completely false claims. All three get dropped. The verdict doesn't move."

### optional 20s beat — the whole argument on one screen

```bash
python -m quorumpilot explain examples/proposal_risky.json
```

> "And if you want the entire argument in one screen: every specialist, every
> citation, every dropped claim with the reason it was dropped, the tally, and
> the ruling. Re-runnable, line by line — that is what 'the agent that can
> explain why' means in practice."


## 2:05 — The book is never in one file (20s)

Gradio → **Fragmented sources** tab, or terminal:

```bash
python -m quorumpilot ingest examples/fragmented/account.json \
  examples/fragmented/broker_a_positions.csv \
  examples/fragmented/venue_b_positions.json \
  examples/fragmented/prices.csv examples/fragmented/policy.json \
  --proposal examples/fragmented/proposal.json
```

Point at the table: five files, four formats, three different column naming
schemes, merged into one book. Then the conflict line:

> "EURUSD appears in broker_a_positions.csv (100,000 units) and venue_b_positions.json (120,000 units); keeping the first."

> "Every merged field keeps provenance — file plus row. When two sources disagree it says so instead of quietly picking one."

## 2:25 — It's a real MCP server (15s)

```bash
python -m quorumpilot mcp
```

then show a `tools/list` response with the six tools, and one `tools/call` for `review_trade`.

> "Protocol 2025-11-25, zero dependencies, and responses are never sliced into invalid JSON."

## 2:40 — Close (15s)

- `194 assertions, offline` — `python eval.py`
- "Standard library only. No API key required. Agents propose, the verifier decides what counts, the arbiter decides what to do."

## YouTube metadata

**Title** (pick one):
- `QuorumPilot — the AI risk committee that throws out claims it can't prove`
- `I built an AI agent quorum where hallucinated numbers lose their vote`

**Description**

```
QuorumPilot reviews a trade before you place it using a quorum of four
specialist agents — analyst, skeptic, risk and compliance.

The twist: an agent may propose any claim it likes, but every claim must cite
a field in the computed facts. A deterministic verifier re-resolves each
citation and discards anything it cannot prove. Only survivors vote
(objection -4, caution -2, support +1), and the arbiter is pure arithmetic —
no model participates in the decision.

Built for The Rise of AI Agents Hackathon (Dubai AI Week / lablab.ai),
Collaborative Systems + Agentic Workflows tracks.

0:00  the problem
0:15  the reckless ticket (7 rule breaches)
0:55  PROCEED / PROCEED_WITH_CAUTION / REJECT
1:25  proving every claim (and dropping the lies)
2:05  the book is never in one file (5 sources merged, conflicts reported)
2:25  MCP server, protocol 2025-11-25
2:40  194 offline assertions

Standard library only — no pip install, no API key needed.
Code: https://github.com/Zhiyilang/quorumpilot-openagent
Not financial advice.
```

**Tags**: `ai agents`, `agentic workflows`, `multi-agent systems`, `risk management`, `mcp`, `model context protocol`, `hallucination`, `python`, `stdlib`, `hackathon`, `lablab`, `dubai ai week`, `deriv`, `trading risk`, `gradio`

**Pre-upload checklist**

- [ ] Video under 3:00
- [ ] Terminal font large enough to read on a phone (18px+)
- [ ] Audio audible without headphones
- [ ] Repo public, README renders, `python eval.py` passes on a clean clone
- [ ] Description links to the repo
- [ ] No API keys visible anywhere on screen
