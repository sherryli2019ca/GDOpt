# GDOpt 结果总表（截至 2026-10-29）

本文件是所有已完成实验的单一入口；细节见各子目录的报告。所有 τ² 实验除非另注：DeepSeek 直连 `deepseek-chat`
（返回模型名 `deepseek-flash`）作 agent 与 user simulator，温度 0，seed 300，Jev = `typesafe/jev-1.14`
（OpenRouter `/api/alpha/decisions`）。贡献表述统一为 **“对输入扰动的决策稳定性”**，不是逐位确定性。

## 1. 主结果：Jev 不确定处加固（pass^k，%）

门控：Jev 对“下一步动作”（message + 各工具）的 p_max < 0.8 视为不确定步（约 30–37% 的步）。

- **deliberate**：在不确定步附加提示“该步在 A/B 之间不确定，请引用政策、检查前提再决定”。
- **reasoner**：不确定步改由 `deepseek-reasoner` 生成。
- **rules**：5 条手写、按政策条款编译的禁止规则（取消资格、已飞航段、支付组合等），E1 审计中 0 次误伤。
- **consistency**：一致性检查（硬：乘客 DOB 必须与档案一致；软 → reasoner 复核：替代性写操作、带未完成事项转人工、
  代码计算报价、最便宜选项检查、basic economy 先升舱再改签提示）。

### Airline（50 任务 × 4 trials）

| 配置 | pass^1 | pass^2 | pass^3 | pass^4 | flaky | always-fail | 报告 |
|---|---|---|---|---|---|---|---|
| baseline | 76.0 | 68.0 | 63.0 | 60.0 | 28% | 12% | anchor/SUMMARY.md |
| hint / veto / checklist（Jev 自信处锚定） | 75 / 76 / 71 | – | – | 64 / 60 / 56 | 22–30% | – | anchor/REPORT.md |
| deliberate | 79.5 | 70.7 | 65.5 | 62.0 | 32% | 6% | anchor/SUMMARY.md R2 |
| reasoner | 80.0 | 73.3 | 69.5 | 66.0 | 26% | 8% | 同上 |
| deliberate_all（对照：每步都提示） | 75.5 | 64.3 | 57.5 | 52.0 | 42% | 6% | 同上 |
| deliberate+reasoner 第 1 次 | 82.0 | 77.0 | 74.0 | 72.0 | 18% | 10% | 同上 R2b |
| deliberate+reasoner 第 2 次（E3，+rules 仅触发 2 次） | 81.5 | 73.7 | 68.0 | 64.0 | 28% | 8% | rules/E3_REPORT.md |
| deliberate+reasoner 合并 8 trials | 81.8 | 75.8 | 71.8 | 68.9 | – | 8% | rules/REPORT.md |
| policy 检索 / policy+reasoner / 3 样本投票 | 77.5 / 79 / 74.5 | – | – | 64 / 62 / 56 | 22 / 28 / 30% | – | anchor/VOTE_POLICY.md |
| **E4：deliberate+reasoner+rules+consistency** | **84.5** | **81.0** | **78.5** | **76.0** | **14%** | 10% | rules/REPORT.md, rules/e4_compare.json |

配对 bootstrap（按任务重采样）：
- deliberate+reasoner 第 1 次 vs baseline：Δpass^1 +6 [+0.5, +12.5] P=0.98；Δpass^4 +12 [0, +24] P=0.97。复现后合并 8 trials 的 pass^4 ≈ 69，**72 偏乐观**。
- E4 vs baseline：Δpass^1 +8.5 [+2.5, +15] P=1.00；Δpass^4 +16 [+4, +30] P=0.99（任务 13 好 / 4 差）。
- E4 vs deliberate+reasoner 合并 8 trials：Δpass^1 +2.8 P=0.89；Δpass^4 +7.1 [−1.3, +15.8] P=0.95。
- E4 只有 1 次运行；同配置两次运行 pass^4 相差 8 点 → **论文规则：每个 pass^4 结论需 ≥2 次运行或跨域复现**。

### Retail（114 任务 × 4 trials）

| 配置 | pass^1 | pass^2 | pass^3 | pass^4 | flaky | always-fail |
|---|---|---|---|---|---|---|
| baseline | 82.7 | 75.0 | 70.2 | 66.7 | 28.1% | 5.3% |
| deliberate+reasoner | 84.4 | 77.8 | 73.9 | 71.1 | 24.6% | 4.4% |
| + retail 一致性检查 | 86.6 | 79.2 | 74.1 | 70.2 | 27.2% | 2.6% |

- D+R vs baseline：Δpass^1 +1.8 P=0.79；Δpass^4 +4.4 [−3.5, +12.3] P=0.85；任务 23 好 / 14 差。方向与 airline 一致，单独不显著。
- +检查 vs baseline：Δpass^1 +3.9 [−0.4, +8.3] P=0.96；Δpass^4 +3.5 P=0.76。vs D+R：pass^1 +2.2，pass^4 −0.9。
  检查只在 456 个 episode 中触发 26 次，能抬 pass^1，推不动 pass^4：retail 失败多源于 user simulator（改主意、
  理由与 gold 不同），可被代码检查的 agent 错误是少数。
- **评测偏差（论文必须注明）**：τ² HEAD 中 40 个带自然语言断言的 retail 任务由 OpenAI 模型评判，本环境 403；
  两组都改用 `deepseek-chat`（T=0）评判（`--nl-judge`）。这 40 个任务的分数不是官方评判。

## 2. 机制发现（零成本日志分析为主）

1. **pass^k 缺口来自输入扰动，不是单步采样噪声。** 固定上下文时 T=0.7 重采样与 T=0 一致 88%，736 次投票只有 14% 分歧；
   跨 trial 对齐步的分叉率约 20%。成功/失败 trial 对的首个分歧 64% 出在 user simulator（常在开场白），
   agent 在相同上下文下自分叉仅 2%。（determinism/instability_sources.json, anchor/VOTE_POLICY.md）
2. **Jev 的不确定性是“哪里会分叉”的定位器，不是“哪边对”的裁判。** 步级分叉风险随 p 单调下降：29%（p<0.5）→ 0.3%（p≥0.95）。
   p<0.8 覆盖 35% 的步、54% 的成败分叉（p<0.9：52% / 72%）。分叉处 Jev 的 argmax 只是跟随本 run 的 LLM，不比它更对。
   （determinism/TRAJECTORY_RISK.md）
3. **定向比干预本身更重要。** 同一提示只在 Jev 不确定步用 → pass^4 +2；每步都用 → −8（P=0.05）。
4. **轨迹级 Jev 风险分不比长度更能预测 flaky**（AUC 0.67–0.77 vs 长度 0.76–0.82）；累计熵门控在等触发预算下覆盖分叉少于逐步 p 门控（24–47% vs 52%）。
5. **固化规则要用政策条款谓词，不是从成功轨迹学“状态→动作”表**（后者只覆盖 1/88 敏感分叉）。条款规则在 1600 条日志中触发 40 次全在失败 episode；
   从违规前一步重放救回 25/38（对照 0/38）。但叠加 reasoner 后几乎不再触发（reasoner 已消除大部分违规）。
6. **失败类型（airline）**：政策违规约 10%；工具对但参数错 33%；不必要的转人工 30%；剩余不一致中还有价格算错、错误拒绝、乘客信息不一致。
   一致性检查局部重放救回 16/44（对照 7/44）。
7. **成本杠杆（早期）**：airline 83% 成本是每步重读的固定前缀 → 整步跳过的节省上限约 5–12%；
   Jev 价格≈flash 级模型，节省 ∝ c_LLM/c_Jev。原始“替换调用省钱”的 replay：节省 ≈5%（reports/replay/SUMMARY.md）。

## 3. 成本

单 episode 成本（token 估算，airline）：baseline $0.0072 → reasoner $0.0105（+46%：Jev ≈ +28%，reasoner 步 ≈ +18%）；deliberate +69%。
百分比高是因为 DeepSeek flash 很便宜；换成 GPT-5.4 级主模型（≈$0.054/task），同样的 Jev 开销 ≈ +4%。与 PolicyGuard 公平比较需同主模型。

累计实际支出（余额差）：DeepSeek 约 ¥117（≈6389 → 6271.99，2026-10-29 查询），其中约 ¥20 浪费在 retail 评判 403 的重试；
OpenRouter $16.38 / $20（含早期 replay ≈ $6、Jev 合计 ≈ $7.7，浪费 ≈ $0.7），**剩余 ≈ $3.6，大实验前需充值**。

## 4. 待定 / 下一步

- E4 配置复现（airline 第 2 次，≈ ¥5.4 + $0.4）——论文规则要求。
- PolicyGuard（arXiv 2606.29225）作基线；更强主模型（成本占比结论依赖于此）。
- RSI（递归自改进）闭环：见设计文档，首个实验零成本离线回放。

## 5. 代码入口

`src/gdopt/adapters/tau2_anchor.py`（全部 anchor 模式）、`tau2_rules.py`（airline 规则与一致性检查）、`tau2_retail_rules.py`；
运行器 `examples/tau2_anchor_replay.py`（`--modes ...`）、`examples/tau2_rule_replay.py`；分析脚本 `examples/determinism/`。
