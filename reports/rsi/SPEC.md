# Do failures already differ at the level of the user's structured request? (2026-11-02)

`examples/determinism/spec_extract.py`: for all 86 trials of E4's 11 flaky airline tasks (8 trials each over E4 runs 1–2;
2 tasks have only 1 success, so 86 are usable), deepseek-chat (T=0, JSON mode) extracts a spec from the user's turns
only (intents, reservation ids, route, dates, cabin, flight criterion, passengers, bags, insurance, payment preference),
at the opening (first 2 user turns) and just before the first write / transfer. Each trial is compared with the
leave-one-out majority of the successful trials of the same task (`spec_extract.json`).

| key field differs from success majority | opening: success / fail | before first write: success / fail |
|---|---|---|
| any key field | 29% / 27% | 84% / 100% |
| intents | 10 / 14 | 37 / 76 |
| flight criterion | 0 / 11 | 18 / 57 |
| passengers | 8 / 0 | 10 / 41 |
| payment preference | 0 / 0 | 33 / 57 |
| cabin | 0 / 0 | 2 / 11 |
| bags / insurance | 0 / 0 | 16–16 / 27–22 |

(n = 49 successes, 37 failures.)

Reading:
- **At the opening, failed and successful trials ask for the same thing** (27% vs 29% differ, the extractor's noise
  level). The instability is not in the first request.
- **By the first write, the failures' requests have drifted**: extra or changed intents (task 23: "change flight"
  instead of cancel-and-rebook), extra flight criteria (tasks 15/16: "shorter connection", "earlier arrival, under $250"
  instead of cheapest), passenger lists, payment wishes, bags/insurance. These are added in the middle of the dialogue,
  in reaction to what the agent showed, which matches the lock-in window (LOCKIN.md).
- So the early-intervention target is the drift of the spec during the dialogue: pin the opening spec, and when a later
  user turn or a proposed action departs from it, make that departure explicit (present options by the pinned
  criterion; confirm a change of criterion; carry nothing from the old reservation that the spec does not state).
  Caveat: a real user may legitimately change their mind; in τ² part of this drift is the simulator leaving its own
  instructions, so an intervention must not simply refuse changes (that would game the benchmark).
- Extraction is noisy for free-text fields (even successes differ 84% before the write once all fields are compared),
  so a spec used online must be small and typed.

Cost: 58.6k input + 19.0k output tokens of deepseek-chat (≈ ¥0.2). Note: the DeepSeek balance dropped ¥9.9 (6243.89 →
6233.99) since the last check right after the proposal-gate run; most of that is presumably delayed billing of that run,
so its real cost is likely ≈ ¥15, not ¥6.14.
