# Proposal-turn cut and proposal gate (airline, 2026-11-02)

Cut points (`proposal_flagged.json`, built by `examples/determinism/proposal_cut.py`): the last agent text message
before the decisive write, i.e. the turn in which the agent puts its plan to the user (2 messages before the write in
64/66 cases). 33 failed trials of E4's flaky tasks + 32 successful trials of the same tasks (harm control; one of the 33
had no text turn before the write). One continuation per cut and arm, seed 400.

- **control**: E4 (deliberate + reasoner at Jev p < 0.8, certified rules, consistency checks).
- **proposal gate** (mode `proposalgate` in `tau2_rules.py`): E4, plus: when the agent's message asks the user to confirm
  a write-like action, (A) the main model is shown the draft and a "Yes, please go ahead" and its write calls are
  recorded; (B) the reasoner, without the draft, independently derives the write the policy and user's request call
  for. If A ≠ B the reasoner rewrites the proposal with both readings and a policy re-check note.

| arm | from failed trials | from successful trials |
|---|---|---|
| control (E4) | 6 / 33 (18%) | 25 / 32 |
| proposal gate | 6 / 33 (18%) | 27 / 32 |

Paired: failed-origin 1 better / 1 worse; successful-origin 2 better / 0 worse. No rescue effect, no harm.

Combined with the point-of-no-return replay (PONR.md), recovery of the same 33 failures by cut point:
first divergence 48% → midpoint 48% → **proposal turn 18%** → right before the write 3%. Most of the lock-in happens
before the agent writes its proposal, in the second half of the window (search results, options offered, the user's
choice), not at the proposal or write itself.

Why the gate does nothing: the gate fired in 30 of 33 failed-origin continuations; at its first check the independent
reasoner derived **the same wrong write as the draft in 20/30**, no write in 8, a different write in 1. This is the third
time (after the 3-sample vote and the write gate, 27/33) that an independent re-derivation from the same context
reproduces the error: by then the context itself points at the wrong action. Re-checking decisions at fixed context
cannot improve stability; the intervention has to change what enters the context earlier (what is asked / looked up /
offered to the user), or make the agent robust to how the user phrases the request.

Gate stats: 132 checks over 331 steps, 40 disagreements (30%), 98 reasoner steps from the Jev gate.

Cost: DeepSeek ¥6.14 (6250.03 → 6243.89; 2× the ¥3 estimate: every proposal costs a reasoner call), Jev + 0 OpenRouter
chat ≈ $0.22 (usage 17.17 → 17.39 of 20).
