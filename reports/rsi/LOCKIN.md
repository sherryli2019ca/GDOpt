# What locks in between the midpoint and the proposal (airline E4, zero cost, 2026-11-02)

Of the 33 E4 flaky failures, 11 recover when continued from the midpoint but not from the proposal turn (5 recover
from both, 17 from neither). For those 11, the original failed trajectory and the successful midpoint continuation
share the same prefix, so the first place they part shows what decided the outcome
(`examples/determinism/lockin_window.py`; grading via τ² action checks).

| type | n | example |
|---|---|---|
| A. user simulator drifts from its instructions after the agent shows details | 4 (tasks 15 ×2, 16 ×2) | agent lists the cheapest $207 itinerary with "LGA layover until 23:00"; user: "that layover is rough, anything earlier?" → picks $216, but the task says cheapest |
| B. step of an agreed multi-step plan never executed | 3 (task 23) | cancel-and-rebook agreed; agent books the three new reservations, never cancels the old one |
| C. attribute of the old reservation carried into the new booking | 2 (tasks 14, 29) | `total_baggages` 6 / `insurance` yes copied over although the user said no bags / no insurance |
| D. payment strategy | 1 (task 23) | one 3-passenger booking (card $1786) instead of three bookings that use all three certificates (card $1286) |
| E. wrong set of reservations identified | 1 (task 42) | cancels a reservation that is not part of the mix-up |

Reading: none of these is a "which branch is right" policy judgment at the proposal. A (4/11) is on the evaluation
side: the simulated user leaves its own instructions when it is shown a menu of options with times (mark separately in
the paper; an agent could reduce it by presenting only the option that meets the stated criterion). B and C are
bookkeeping errors that a code check can see; D and E are planning errors.

Zero-cost audit of two code checks over all 2800 logged airline episodes (`examples/determinism/lockin_checks_audit.py`,
`lockin_checks_audit.json`):

- **slot_provenance** (new booking has insurance / paid bags although the user never asked for them or said no):
  fires in 15 failed vs 5 successful episodes (successes all task 24) → usable as a soft trigger, small coverage
  (15/614 failures).
- **unfinished_cancel** (booked new, a proposed cancel of a known reservation never executed): 28 fail vs 29 success
  (tasks 35 and 24 propose cancel-and-rebook as an option the user declines) → too noisy as a text heuristic; needs a
  structured tracker of user-confirmed plan steps.

Overall: what remains unstable under E4 is a mix of user-simulator drift and small bookkeeping/planning slips, each
covering a few percent of failures. Further code checks give diminishing returns at this level.
