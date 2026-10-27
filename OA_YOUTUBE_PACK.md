# YouTube 上传包 — Open Agent Hackathon 提交视频（零思考，照抄即传）

> 视频文件：`quorumpilot-openagent/oa_demo.mp4`（974,915 B ≈ 952.3 KB · **60.0s**@30fps · 1280×720 · h264 · 无音轨 · 实测 `_mp4_duration.py` PASS）
> 内容全部为**真实命令真实输出**（explain transcript 与 eval section K 均为实跑截取，断言数 194 = 本仓 `python eval.py` 实测 194 passed, 0 failed）

## 上传设置（YouTube Studio）

- **可见性：Unlisted**（未列出，仅链接可看——比赛提交用，先不公开）
- 标题下方 **"No, it's not made for kids"**
- 不需要缩略图（视频自带 hero 帧）
- 上传后**复制视频链接**，回填到 Open Agent 提交表单的视频字段

## 标题（照抄）

```
QuorumPilot — the AI risk committee that throws out claims it can't prove (Open Agent Hackathon 2026)
```

## 描述（照抄）

```
QuorumPilot is a multi-agent review board: four specialist agents
(analyst, skeptic, risk, compliance) propose claims about a trade,
and a deterministic verifier re-resolves every citation and drops
anything it cannot prove. Only survivors vote, and the arbiter is
pure arithmetic — no model participates in the decision.

Built for the Open Agent Hackathon 2026, Track 02 — "The Agent That
Can Explain Why". The in-window increment adds an NVIDIA Nemotron
backend (OpenAI-compatible, zero new dependencies, degrades loudly
without a key) and the `explain` transcript: every specialist, every
citation, every dropped claim with the reason it was dropped, the
tally, and the ruling — re-runnable, line by line.

0:00  the agent that can explain why
0:06  the arbitration transcript (real output)
0:30  eval section K — nemotron backend, offline, no key
1:00  194 assertions, standard library only

194 offline assertions. MIT. No API key required.
Code: https://github.com/Zhiyilang/quorumpilot-openagent
Not financial advice.
```

## 标签（照抄）

```
ai agents, agentic workflows, multi-agent systems, open agent hackathon, track 02, nvidia nemotron, model context protocol, mcp, hallucination, evidence, citations, risk management, trading risk, python, standard library, zero dependency, offline, hackathon 2026
```

## 时间轴（与视频实际内容对应，写描述时已用）

| 时间 | 内容 |
|---|---|
| 0:00 | hero 卡：Open Agent Hackathon 2026 · Track 02 · 194 offline assertions |
| 0:06 | 终端：`python -m quorumpilot explain examples/proposal_risky.json` 真实输出 |
| 0:30 | 终端：`python eval.py` section K 真实输出（nemotron backend + explain transcript） |
| 0:48 | close 卡：194 assertions, offline · MIT · repo 链接 |

## 上传前三查

- [ ] 文件是 `quorumpilot-openagent/oa_demo.mp4`（974,915 B / 60.0s）——**不要**误传 quorumpilot 的 deriv_demo.mp4（那是 Deriv 线素材，76s，指向 quorumpilot 仓）
- [ ] 可见性 = Unlisted
- [ ] 描述里的 repo 链接指向 `Zhiyilang/quorumpilot-openagent`（建仓后生效；10-26 前链接 404 属正常，视频先传着）
