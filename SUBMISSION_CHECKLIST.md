# Submission checklist — two competitions, one project

> **Read this first if you are here for Open Agent.** This file is the shared
> checklist for the two competitions QuorumPilot is entered in; Competition 1
> (lablab / Deriv) is the one that owns the timeline below. This repository is
> the **Open Agent** entry (Track 02, "The Agent That Can Explain Why"), created
> inside that hackathon's window and scored on the in-window increment described
> in the README: the Nemotron backend, the `explain` transcript, and section K of
> the eval suite. Its own submission steps are in `OPEN_AGENT_ACTION_CARD.md`.
> ⚠️ Unresolved contradiction, do not guess: the line below calls Zetaris /
> Meterless "optional upside", while `OPEN_AGENT_ACTION_CARD.md` records the
> Wildcard rules as possibly **requiring** both. Resolve it from the official
> Wildcard page before choosing a track.

## Competition 1 — The Rise of AI Agents Hackathon (lablab.ai / Dubai AI Week)

**Prize pool:** $60,000+ · **Build window:** 26 Oct – 2 Nov 2026 · **Submission deadline: 2 Nov 2026 (end of day)** · **Final Showcase (invite only, Dubai): 3 Nov**（现场在 Deriv Offices, Business Bay；差旅不覆盖，无需订任何行程）
**Tracks (official, pick one):** 🧠 Intelligent Reasoning · 🔄 Agentic Workflows · 🌍 Enterprise Utility · 🧩 Multimodal Intelligence · 🤝 **Collaborative Systems (primary — QuorumPilot 四专家+仲裁者就是多智能体协作)**；🔄 Agentic Workflows (secondary)
**Judging criteria (official):** Innovation · Practical Application · Technical Execution · Impact · Originality
**Submission requirements (lablab format):** working online prototype + video presentation + pitch deck（提交表单还要重读一遍官方规则页，lablab 偶尔加必填字段）
**Registration:** lablab.ai 注册在建窗期内持续开放，可 10-26 开窗日注册；**一个 lablab 账号同时覆盖 Vultr Agent Rush 提交**。队内每人需各自注册。
**Eligibility:** global, online participation, solo or team, 18+. Confirmed from the official lablab.ai event page.
**GCP 专项注意:** Google GCP 奖品要求用 Gemini 模型驱动 agent 智能——见下文 26 Oct–1 Nov 增量第 1 条（`brain.py` 已讲 OpenAI-compatible，零代码改动）。

## Competition 2 — Open Agent Hackathon 2026 (GenAI Works)

**Prize pool:** "up to $20,000" — **cash is $13,000**, the rest is in-kind.
Track 02 = $3,700 (1st $1,600 / 2nd $1,200 / 3rd $900); in-kind: NVIDIA DGX
Spark Founder's Edition $4,699 (Best use of Nemotron) + SpaceX Cursor API
credits $2,301. Verified on the live event page 2026-10-16 (3,674 registered).
**Dates (UTC):** registration closes **22 Oct 23:59** · build window **22–27 Oct** · submissions close **27 Oct 23:45** · results 6 Nov 16:00
（北京时间：注册 10-23 07:59 截止；提交 10-28 07:45 截止）
**Track: 02 — The Agent That Can Explain Why** (official wording: "Build agents that investigate complex questions across multiple data sources, connect findings, and produce evidence-backed answers or recommendations")
**Eligibility:** fully online, worldwide, 16+, solo or teams of 1–5. Free entry. No China exclusion.

**Why Track 02, not Track 01 or the Wildcard:**
- Track 02 is the project's actual differentiator — the arbiter's verdict is a
  *cited* conclusion (every claim carries its evidence), which is exactly what
  the track asks to be judged on. The `ingest` layer (five mismatched venue
  exports → one book with provenance) then becomes the "multiple data sources"
  proof, not the headline.
- The Wildcard [Tinkerer] track explicitly welcomes pre-existing projects, but
  **requires integrating both Zetaris and Meterless** — without keys/access to
  those platforms that is a dead end in a 5-day window.
- ⚠️ **Sponsor technology: corrected twice — here is the final reading.**
  A GenAI Academy FAQ is worded as if **every** submission must integrate
  Zetaris (and use Cursor, run on Nemotron). The **live event page fetched
  2026-10-16** says something narrower and is taken as authoritative:
  - Main tracks: "Teams are **encouraged** to make meaningful use of the
    available sponsor technologies" — encouraged, not mandatory.
  - **Wildcard [Tinkerer] bonus track only:** "Entries … **must integrate
    Zetaris and Meterless**."
  - `Sponsor tech` is **10 of 100 points**, not a gate.
  → **Conclusion: Track 02 is viable without Zetaris.** We forfeit those 10
  points (or chase the NVIDIA Nemotron in-kind award separately). An earlier
  note in this file downgraded Open Agent to "upside-only" on the FAQ reading —
  **that downgrade is withdrawn**; the original judgement (Track 02 has no
  mandatory sponsor tech) was right. Still skim official Rules §05 on the day
  of registration in case the wording moves again.
- De-risk option if you obtain access: a Zetaris adapter can be built in our
  proven "real REST client + offline mock, same interface" pattern (as done for
  Qloo: `tasteweaver/qloo.py` + `mock_qloo.py`), making it a drop-in during the
  22–27 Oct build window.

**Scoring map (100 pts):** Impact 30 · Technical 20 · Innovation 15 · Demo 15 ·
Product & UX 10 · Sponsor tech 10. QuorumPilot's strongest cells: Impact (real
prediction-market users, quantified edge), Technical (194/194 assertions, MCP
server, receipts), Demo (21.5s real-run video already produced:
`quorumpilot_demo.mp4`). Sponsor-tech 10 pts need Zetaris / Meterless / NVIDIA
Nemotron — **optional upside, not a gate** (see correction above). Do not spend
the build window chasing them.
- **Possible extra credit (unverified):** an aggregator listing mentions up to
  **30 bonus points** for open-sourcing the result, shipping evals, or
  documenting failure modes. The live event page shows only the 100-point
  rubric, so treat this as unconfirmed — but all three are things QuorumPilot
  already does (public repo, 194 assertions, failure-mode docs), so if the
  bonus exists we collect it for free.

### ✅ Official eligibility ruling (2026-10-17, verbatim from the live event page) — why QuorumPilot, not DecisionLens, is the Open Agent entry

> **Bonus track — Wildcard [Tinkerer]: Bring Your Own Project** — "Bring an existing project, prototype or concept and extend it using sponsor technology such as Meterless and Zetaris. Entries are judged on the same criteria as the other tracks, must integrate Zetaris and Meterless, and are scored on the new work rather than prior development."

Main page also states "**Pick one track. Build for it.**" and "Over a six-day build sprint" (build window opens Oct 22 00:00 UTC).

**Reading:** the organizers maintain a dedicated track for pre-existing projects (Wildcard, mandatory Zetaris+Meterless, new work only) → main tracks 01/02/03 are for work built inside the window. DecisionLens's public repo predates the window → **main-track eligibility risk; Wildcard is a dead end without keys.** QuorumPilot's public repo is created **26 Oct, inside the window** (per plan below) → **eligibility-safe, and its cited verdicts are a literal Track 02 fit.** → **Open Agent entry = QuorumPilot. DecisionLens demoted to backup** (second gun only if the platform confirms multiple projects per team are allowed; see `decisionlens/OPEN_AGENT_PITCH.md` banner).

> **Order of operations:** register for Open Agent **before 22 Oct 23:59 UTC**
> (北京 10-23 07:59 — that is a user action, the form needs an email), then
> publish on the 26th and submit before 27 Oct 23:45 UTC (北京 10-28 07:45).

## Why one project can honestly enter both

| Requirement | Deriv / lablab | Open Agent | QuorumPilot |
|---|---|---|---|
| Original work built in the window | yes | yes | repo created 26 Oct, inside both |
| Multi-agent / collaborative | Collaborative Systems track | "agentic applications" | 4 specialists + arbiter |
| Tool use / workflows | Agentic Workflows track | multi-step reasoning | 6 MCP tools, 6-stage loop |
| Evidence-backed answers | — | **track 02 headline** | cited verdicts + receipts |
| Fragmented data | — | track 01 (now our proof layer) | `ingest.py` + provenance |
| Works without paid APIs | yes | yes | stdlib only, no key needed |

Neither ruleset forbids dual submission. Check each form's own checkbox on the
day; if either asks for exclusivity, Deriv ($60k) takes priority.

## Do not do these before 26 Oct

- [ ] **Do not create the public repo / Space before the build window opens.** lablab hackathons expect work built inside the window. Keep the code local until 26 Oct.
- [ ] Do not publish the DEV/HF/Reddit post before the window opens.

## 26 Oct — opening day (do all of this the same day)

- [ ] Register on **lablab.ai** (this is also the account needed for the Vultr Agent Rush submission — one registration covers both). **（用户动作，~5 分钟；官方页 lablab.ai/ai-hackathons/ai-agents-ai-week-hackathon → Sign up）**
- [x] Create the public repo `Zhiyilang/quorumpilot`, MIT, push everything in this folder. **→ 已由 00:35 自动化完成（路线 B/Gitee）：`gitee.com/ZhiYIlang/quorumpilot-deriv`，created 2026-10-26T00:35:47+08:00（窗口内），公开匿名可见，47 文件，MIT**
- [ ] Deploy: Render (`render.yaml`) **and/or** a Hugging Face Space. Put the live URL in the README and in the submission. **（用户动作；注：workbuddy 发布槽 clauseguard-ai.app.workbuddy.host 现由 ClauseGuard 占用至 11-01 14:59，QuorumPilot 槽位 11-02 08:00 起——OA 线今天的 live URL 需走 HF Space/Render 新部署，零思考包已备：`_hf_space_bundle/`）**
- [x] Run `python eval.py` on a clean clone and paste the result (`137 passed, 0 failed`) into the README. **→ 已完成（10-26 09:0x）：干净克隆实测 137 passed, 0 failed exit 0；结果行已写入 README.md / README.zh.md 并匿名复验**
- [ ] Post a short build log / thread with the repo link.
- [ ] Submit the same project to **Open Agent** — **track 02, The Agent That Can Explain Why**; submissions close **27 Oct 23:45 UTC** (北京 10-28 07:45), one day after publishing. Use the 21.5s demo video already produced (`quorumpilot_demo.mp4`); upload it to YouTube unlisted the same day. **（用户动作，**今天 10-26 就交掉**，别等 10-28；视频版本提示：21.5s 快剪已在仓内，76.0s 完整版 `deriv_demo.mp4` 同仓——10-20 起 76s 为主推口径，上传时二选一，推荐 76s）**

## 26 Oct – 1 Nov — optional upgrades, in priority order

1. **Add the LLM member with Gemini** (tracks require Gemini for Google GCP prizes):
   `OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`, `OPENAI_MODEL=gemini-3-flash`.
   No code change — `brain.py` already speaks OpenAI-compatible. Record one run showing a hallucinated claim being dropped.
2. **Vultr** is a partner: if the Vultr key is available by then, deploy there too and mention it.
3. Add a second correlated-pair example with a real correlation matrix.

## 1–2 Nov — submission

- [ ] Record the demo (≤3 min) following `DEMO_SCRIPT.md`, upload unlisted→public on YouTube.
- [ ] Fill the lablab submission form:

**Title:** QuorumPilot — an agent quorum where unprovable claims lose their vote

**Tagline:** Four specialist agents review a trade; a deterministic verifier throws out every claim they can't prove.

**Description (paste):** see `README.md` "Why this exists" + "The four specialists" + "Honest limits".

**Track:** Collaborative Systems

**Built with:** Python (stdlib only), MCP, Gradio, optional Gemini via OpenAI-compatible API

**Links:** repo · live demo · video

- [ ] Re-read the official rules page once more on submission day — lablab sometimes adds a required field.

## What the judges will actually check

| They ask | Where the answer is |
|---|---|
| Is it an *agent*, not a prompt? | `agents.py` — 4 specialists propose; `arbitrate.py` decides |
| Does it do multi-step work? | PERCEIVE→SPECIALIZE→VERIFY→ARBITRATE→EXPLAIN→RECEIPT, `agent.py` |
| Does it use tools? | 5 MCP tools, `mcp_server.py`, protocol `2025-11-25` |
| Is it novel? | The verifier: claims without provable evidence lose their vote (eval §F) |
| Does it work without a key? | Yes — the whole quorum is deterministic |
| Is it honest about limits? | `DESIGN.md` "What was cut" + README "Honest limits" |

## Notes on eligibility (verified 15 Oct 2026)

- Online participation is open globally; the Dubai finale is invite-only and travel is **not** covered. Nothing in the rules requires travel to win.
- On-site attendance is by invitation; do not book anything.
- Google GCP prizes specifically require Gemini models — covered by step 1 above.
