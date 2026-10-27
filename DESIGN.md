# Design notes

## The one idea

> Agents may propose. The verifier decides what counts. The arbiter decides what to do.

Everything else follows from that sentence. It is also the answer to the question "what happens when the model hallucinates?" — the hallucination is dropped, visibly, and the receipt says why.

## Why a quorum instead of one agent

A single agent asked to review its own plan has no incentive to disagree with itself. Four specialists with different jobs do:

- `analyst` is allowed to like the trade.
- `skeptic` is *required* to attack it (and to say "no objection survives" when nothing does — a skeptic that always objects is noise).
- `risk` only reports money.
- `compliance` only reports rules, one claim per breach, no discretion.

The disagreement is the product. The arbiter's job is to turn disagreement into a decision without ever resolving it by "the model's judgement".

## Why claims, not verdicts

An agent that outputs `REJECT` is un-auditable. An agent that outputs

```
stance=objection
statement="correlated risk would be 13.60%, above the 5.00% cap (EURUSD(0.70), XAUUSD(0.70))"
evidence=[metrics.correlated_risk_pct → "13.60", metrics.correlated_with → "['EURUSD(0.70)']"]
```

can be checked. `verify.py` re-resolves `metrics.correlated_risk_pct`, parses the number out of the excerpt, and compares with `max(tolerance=0.02, 1% of value)`. If the claim says `0.02%` when the field says `10.00`, the claim dies.

This is also what makes the LLM member safe: the prompt hands the model a closed locator→value map and tells it to cite nothing else. The model is free to be wrong; it is not free to be believed.

## Why the arbiter is arithmetic

```python
if hard_breach:            REJECT
elif any_objection:        REJECT
elif score < 0:            PROCEED_WITH_CAUTION
else:                      PROCEED          # weights: -4 / -2 / +1
```

No model participates. A rule breach is a comparison of two floats. The score is a sum of fixed weights. A judge can read `arbitrate.py` in two minutes and predict every verdict the system will ever produce on a given input — that is the property worth having in a risk tool.

## Why "risk" and not notional

The first version measured concentration as `notional / equity`. For a leveraged instrument that number is 500% on a completely ordinary ticket, so the rule fired on everything and the tool was useless. Exposure is now measured as **cash at risk if the theme goes against you**:

```
risk_concentration_pct = (risk on this symbol) / equity
correlated_risk_pct   = (risk on this symbol + risk on correlated positions) / equity
```

Correlation defaults to a currency-overlap heuristic (same base or same quote → 0.7), never a fabricated precise number, and the receipt labels it as an approximation.

## Why the suggestion is a number and not advice

`REJECT` alone is annoying; `REJECT, but 70,000 units fits` is useful. `suggest_units` solves each binding cap independently and takes the **minimum**:

| Breach | Solve |
|---|---|
| `RISK_PER_TRADE` / `TOTAL_RISK` | `units = equity × cap% / stop_distance` (shares the portfolio budget with what's already open) |
| `LEVERAGE` | `units = equity × max_leverage / entry` |
| `RISK_CONCENTRATION` / `CORRELATED_RISK` | `units = remaining risk budget / risk per unit` |

It never returns a size larger than the one proposed. And it can't fix everything — a 1:1 reward:risk stays broken at any size, so the tool says that instead of inventing a fix.

## Failure modes, deliberately

| Situation | Behaviour |
|---|---|
| No API key | Deterministic quorum, receipt says `brain=offline-deterministic` |
| LLM unreachable / returns garbage | Degrades, receipt says so, quorum still completes |
| LLM invents numbers | Claims dropped with reasons; verdict unchanged (tested) |
| Unreadable position row | Skipped, counted, reported in the receipt |
| No stop on the proposal | Hard `NO_STOP` breach; `solve_units_for_risk` returns 0 rather than guessing |
| Malformed JSON input | CLI/app return a readable error, no traceback |
| Hostile symbol (`</script><img onerror=...>`) | Escaped in HTML receipts (tested) |
| MCP response too large | Shrunk structurally; never sliced into invalid JSON |

## What was cut

- **Signal generation.** It does not tell you what to buy, only whether a plan survives your own rules. Adding "should I buy" would put an unverifiable claim at the centre of the system.
- **Backtesting / historical win rates.** Tempting, unverifiable from the inputs, and easy to dress up as insight.
- **Broker integration.** Placing orders is exactly the action that must stay with a human.
- **A confidence score.** The arbiter's score is already a sum of fixed weights; adding a model-generated confidence would let the model vote twice.
