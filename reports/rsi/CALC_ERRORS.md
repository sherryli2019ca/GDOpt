# What kind of errors are E4's flaky failures? (zero cost, 2026-11-02)

**Correction (LEDGER.md):** most "agreed step never executed / gold write never made" cases are wrong refusals — the agent told the customer the cancel/change was not allowed — not forgotten steps. Read the bookkeeping share below as an upper bound.

`examples/determinism/calc_errors.py`, `calc_errors.json`: every failed trial of the two E4 airline runs (8 trials per
task) is compared with the task's gold write actions; the first gold write that is not reproduced is classified by
the argument that differs (slot arguments are checked before payment amounts, so an amount difference caused by e.g.
added insurance counts as an insurance error). For tasks 15/16 the first price the agent quotes is also checked.

37 failures in flaky tasks (11 tasks):

| type | n | where |
|---|---|---|
| agreed step never executed: cancel of the old / duplicate reservation | 8 | 23 ×4, 14 ×2, 29, 42 |
| other gold write never made | 6 | 44 ×5 (flight change of one reservation), 8 |
| attribute not from the user: insurance 5, bags 1, passengers 1 | 7 | 29 ×5, 14, 23 |
| user picks a non-cheapest option after the agent shows details (first quote was the true cheapest $207) | 5 | 15, 16 |
| calculation: first quoted "cheapest" wrong (2), payment amount (2), payment split (1) | 5 | 15/16, 33 ×2, 29 |
| extra write | 3 | 6, 42, 45 |
| other flight selection | 2 | 44 |
| writes correct (DB side effect) | 1 | 14 |

32 failures in always-fail tasks (7, 18, 32, 39): missing write 24, extra write 6, amount 2.

Reading:
- **Pure calculation errors are rare under E4: 5/37 (14%).** E4's code pricing / cheapest checks already make the
  first quote right in most trials (in E4's 7 failures of tasks 15/16 the first quote was the true cheapest in 5). A
  deterministic "cheapest itinerary / amount" executor would address at most ~5 of 37.
- **Bookkeeping is the largest share: 21/37 (57%)** — steps of an agreed plan that never happen (14) and booking
  attributes that do not come from the user (7). Both are about state, not judgment: a structured plan ledger
  (user-confirmed steps → check all executed before closing) and slot provenance (every new-booking attribute must be
  traceable to a user statement; audit: 15 failed / 5 successful episodes) are deterministic executors in GDOpt's sense.
- User-simulator drift 5/37 (14%) is evaluation-side.
- Agent self-corrections ("I made an error", "correction") appear in 7/69 failures and 15/331 successes (10% vs 5%).
