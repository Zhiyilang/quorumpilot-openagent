# QuorumPilot

**一个由多个 AI 智能体组成的"评审团"，在你下单之前审查这笔交易——再用一个确定性验证器，把智能体们无法证明的每一个论断全部丢弃。**

大多数"AI 智能体"是一个模型加一串工具。QuorumPilot 是一个**有规则的委员会**：四位专家围绕一笔待执行交易展开辩论，他们提出的每个论断都必须引用计算事实中的某个字段，任何无法被证明的论断在投票前就被丢弃。仲裁者——纯算术，不用模型——把幸存下来的论断汇总成三种裁决之一：`PROCEED`（执行）、`PROCEED_WITH_CAUTION`（谨慎执行）、`REJECT`（拒绝）。

```
感知 → 分工 → 验证 → 仲裁 → 解释 → 回执
       4 智能体  逐条证明  决策   说明理由  全程记录
```

**智能体只能提议。验证器决定什么算证据。仲裁器决定该怎么做。**

---

## 演示

- **`quorumpilot_demo.mp4`** —— 21.5 秒快剪：高风险订单被拒的全过程。
- **`deriv_demo.mp4`** —— 76.0 秒完整演示：三种裁决、验证器丢弃无法证明的论断、MCP 服务器（全部真实运行、真实输出；eval 场景中断言数已于 2026-10-22 帧级修正为真实的 137）。

两个文件都在本仓；比赛提交另附 YouTube unlisted 链接。

---

## 为什么做这个

问一个 LLM"这笔交易该不该做"，它会自信满满地回答，并引用它自己编造出来的数字。那不是风险工具，那是负债。QuorumPilot 把通常的安排倒过来：

- 模型（或基于规则的专家）**提出**论断。
- 确定性验证器把每条引用对照事实包解析核对，**丢弃**数字对不上的论断。
- 只有通过验证的论断才能投票，且权重固定：反对 −4、警示 −2、支持 +1。
- 规则突破是算术计算出来的，模型没法靠嘴皮子绕过硬顶。

如果你接入的语言模型产生了幻觉，你会看到它的论断落在**"已丢弃"**区，并附丢弃原因。裁决结果不变。这个性质有测试保证（`eval.py` F 节："会撒谎的智能体失去投票权"）。

## 四位专家

| 智能体 | 争论什么 | 拒绝做什么 |
|---|---|---|
| `analyst`（分析师） | 这个设置值不值：盈亏比、止损距离、周期匹配 | 说"好交易" |
| `skeptic`（怀疑论者） | 为什么这是同一注押了两次：相关性、集中度、保证金 | 安抚人 |
| `risk`（风控） | 钱的事：风险现金、最差情况权益、之后剩余保证金 | 往有利方向取整 |
| `compliance`（合规） | 逐条政策规则，每次突破一条论断 | 豁免任何规则 |

可选的第五位成员（任何 OpenAI 兼容端点，包括 Gemini）可以加入。它拿到的是**一份封闭的定位符清单及其精确取值**，除此之外不许引用任何东西。

## 快速开始

```bash
git clone https://github.com/Zhiyilang/quorumpilot && cd quorumpilot
python -m quorumpilot review examples/proposal_risky.json
```

无需安装、无需 API Key、无需网络。Python 3.8+，纯标准库。

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

这个建议不是和稀泥：在 70,000 手下，这笔单能通过七项突破中的六项。第七项（`REWARD_RISK`）无法靠改手数解决，工具会明说，而不是悄悄略过。

## 三个示例

| 示例 | 内容 | 裁决 |
|---|---|---|
| `proposal_risky.json` | 权益的 10% 置于风险、25 倍实际杠杆、保证金放不下、1:1 盈亏比、叠在两笔同货币持仓上 | `REJECT`（7 项突破，建议 70,000 手） |
| `proposal_clean.json` | 0.06% 风险、2.3:1 盈亏比、保证金不动 | `PROCEED` |
| `proposal_caution.json` | 无突破，但已用 73% 风险预算、与一笔 EURUSD 持仓相关、自由保证金降到 5.5% | `PROCEED_WITH_CAUTION` |

中间那个案例和第一个一样重要：一个永远说不的风险工具毫无用处。

## 输入

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

除 `proposal` 外全部可选——缺的项用合理默认值补齐。读不懂的行会被跳过并报告，绝不静默丢弃。

### 默认政策

| 规则 | 默认值 | 含义 |
|---|---|---|
| `max_risk_pct_per_trade` | 2.0 | 每单风险现金，占权益 % |
| `max_total_risk_pct` | 6.0 | 持仓 + 待执行，占权益 % |
| `max_leverage` | 30.0 | 实际杠杆 = 名义价值 / 权益 |
| `max_risk_concentration_pct` | 4.0 | 单一 symbol 的风险资本 |
| `max_correlated_risk_pct` | 5.0 | 相关品种间的风险资本 |
| `min_rr_ratio` | 1.5 | 盈亏比下限 |
| `max_positions` | 8 | 持仓数量上限 |
| `min_free_margin_pct` | 20.0 | 自由保证金下限，占权益 % |
| `max_stop_pct_of_price` | 8.0 | 宽于此的止损会被标记 |

敞口按**风险**计量，不按名义价值：普通杠杆单的"名义/权益"轻松 500%，那样会禁掉一切。如果两个品种共用基础货币或报价货币，默认按 0.7 相关处理（除非你提供相关矩阵）——并且回执会注明这是近似值，不是测量值。

## 碎片化数据源

你的风险数据从来不在一个文件里。把手头任何导出丢进来——列名为 `Instrument,Qty,Avg Price,Stop` 的 CSV、用 `market/size/open/sl` 的 JSON 转储、价格文件、扁平账户对象、政策对象——QuorumPilot 会判断每个文件是什么、把它们关联起来，审查合并后的账簿。

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

没有任何东西会被静默覆盖。`EUR/USD` 和 `EURUSD` 被识别为同一品种，价格按品种关联，**每个合并字段都保留来源**（源文件 + 行号）。两个来源冲突时，冲突会被打印出来，第一个来源获胜——回执会说明这一点，而不是假装分歧不存在。

## 接口

**CLI**

```bash
python -m quorumpilot review examples/proposal_risky.json --json
python -m quorumpilot review examples/proposal_risky.json --html receipt.html
python -m quorumpilot facts  examples/proposal_clean.json
python -m quorumpilot policy examples/proposal_risky.json   # 有突破则退出码 1
python -m quorumpilot mcp                                    # stdio 上的 MCP
```

**MCP 服务端**（零依赖，协议版本 `2025-11-25`）：

`load_snapshot` · `review_trade` · `explain_verdict` · `policy_check` · `suggest_size` · `ingest_sources`

```bash
python -m quorumpilot mcp
```

**Gradio 应用**——两个页签：*单一账户* 和 *碎片化数据源*（可丢多个导出文件）。

```bash
python app.py          # 同时通过 /gradio_api/mcp/ 提供 MCP
```

**接入语言模型**（可选——以上功能全部无需模型）：

```bash
export OPENAI_API_KEY=...                 # 任何 OpenAI 兼容端点
export OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
export OPENAI_MODEL=gemini-3-flash
```

模型拿到的是封闭定位符清单，不许引用清单外的东西。如果它连不上，评审团会在回执里说明，然后仅以确定性专家运行。

## 测试

```bash
python eval.py        # 194 条断言，离线
python -m quorumpilot explain examples/proposal_risky.json
                       # 打印整场仲裁转写
```

**最新一次运行：137 passed, 0 failed**——2026-10-26 在公开仓的干净克隆上实测（退出码 0，仅标准库，无网络）。

覆盖算术、全部九条规则、验证器的七条拒绝路径、仲裁器的三种裁决、真实子进程上的 MCP 协议、CLI、HTML 注入安全，以及上述安全性质：一个编造了三条自信、合理、完全错误的论断的"大脑"，**三条全部被丢弃**，裁决不变。

## 诚实的边界

- 它告诉你一个计划能否在*你自己的规则*下存活，从不告诉你该买什么。
- 相关性默认用货币重叠近似，有矩阵请提供。
- 手数建议只能修手数，坏的盈亏比不会变好。
- 单时间框架，对新闻、财报、流动性缺口一无所知。
- 不构成投资建议，这里没有任何东西会下单。

## 目录结构

```
quorumpilot/
├── quorumpilot/
│   ├── market.py        # 解析 + 算术 + 规则引擎（不带观点）
│   ├── agents.py        # 4 位专家；每条论断必须引用证据
│   ├── verify.py        # 解析每条引用；丢弃无法证明的
│   ├── arbitrate.py     # 唯一做决策的地方
│   ├── brain.py         # 可选 LLM 成员，可见地降级
│   ├── agent.py         # 感知→…→回执
│   ├── receipts.py      # JSON + 自包含 HTML
│   ├── mcp_server.py    # stdio MCP，spec 2025-11-25
│   ├── ingest.py        # 碎片化数据源 → 单一账簿 + 来源
│   ├── cli.py           # + explain 子命令
│   ├── nemotron.py     # NVIDIA Nemotron 后端（窗内新增）
│   └── explain.py      # 裁决转写（窗内新增）
├── examples/            # 鲁莽 / 干净 / 边缘
│   └── fragmented/      # 5 个互相不一致的场所导出
├── app.py               # Gradio（+ MCP 端点）
└── eval.py              # 194 条断言（窗内新增 57 条）
```

---

## 赛窗内新增（Open Agent 黑客松，Track 02）

本仓库在赛事报名窗口开启后创建，评分只看窗内新增的工作。三件事是新的：

**1. NVIDIA Nemotron 后端**（`quorumpilot/nemotron.py`）。沿用项目既有的 `Brain`
接口，指向 NVIDIA 的 OpenAI 兼容端点，纯标准库。模型会拿到一份封闭的定位符清单
及其精确取值，并被要求不得引用清单外的内容——但它可以不听，因为
`quorumpilot.verify` 才是闸门：幻觉出来的定位符或对不上的数字，代价是模型自己
那条论断在回执里被丢弃，而不是用户的钱。没有 key 或调用失败时，它会响亮地降级
到确定性四专家，并在回执里写明。

**2. "为什么"裁决转写**（`python -m quorumpilot explain FILE`）。一份碎片化
证据进去，整场仲裁出来：每位专家提出了什么、引用了哪条证据、哪些论断没过核验
以及原因、比分如何、仲裁者据此做了什么。每一条都可以对着原始文件复跑——这正是
Track 02 要的东西。

**3. 两者的测试**（`eval.py` 第 K 节）：新增 57 条断言，全套来到 194 条断言，
全部离线、不需要 API key。端点是被伪造的，"绝不编造"这条性质正是这样被实测的：
一个说谎的 Nemotron 大脑会被看到三条论断全被核验器判负、裁决分毫不变。

设置 `NEMOTRON_API_KEY`（build.nvidia.com 免费额度）即可启用 LLM 层；不设置则
确定性四专家跑完全相同的流水线，演示照样产出完整转写。

## 许可证

MIT，见 `LICENSE`。
