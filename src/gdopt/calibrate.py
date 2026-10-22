"""Stage 4b: choosing the global knob with a statistical guarantee.

We want the transformed agent's task failure rate to exceed the original
agent's by at most ``eps``, with probability at least ``1 - delta`` over the
calibration draw.  Risk is monotone in ``lam`` (larger ``lam`` means more
fallback), so Learn-then-Test with fixed-sequence testing applies: walk from
the most conservative ``lam`` downwards and stop at the first one whose
null hypothesis "risk increase > eps" cannot be rejected.

The p-value is computed on paired per-task loss differences
``d_i = loss_lam(i) - loss_base(i)`` in [-1, 1], by default with the empirical
Bernstein bound (variance-adaptive; most paired differences are 0 because the
two agents agree on most tasks, which is exactly where Hoeffding is far too
loose).  Roughly, certifying ``eps = 0.05`` at ``delta = 0.1`` needs about 500
calibration tasks when the agents rarely disagree; Hoeffding needs thousands.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence


def hoeffding_p_value(diffs: Sequence[float], eps: float) -> float:
    n = len(diffs)
    if n == 0:
        return 1.0
    mean = sum(diffs) / n
    if mean >= eps:
        return 1.0
    return math.exp(-n * (eps - mean) ** 2 / 2.0)


def empirical_bernstein_upper(diffs: Sequence[float], delta: float) -> float:
    """Upper confidence bound on E[d] for d in [-1, 1] (Maurer & Pontil, 2009).

    Variance-adaptive: paired task losses mostly cancel, so the bound is much
    tighter than Hoeffding's when the two agents rarely disagree on a task.
    """
    n = len(diffs)
    if n < 2:
        return 1.0
    s = [(d + 1.0) / 2.0 for d in diffs]  # rescale to [0, 1]
    mean = sum(s) / n
    var = sum((x - mean) ** 2 for x in s) / (n - 1)
    ln = math.log(2.0 / delta)
    ub = mean + math.sqrt(2.0 * var * ln / n) + 7.0 * ln / (3.0 * (n - 1))
    return 2.0 * ub - 1.0


def empirical_bernstein_p_value(diffs: Sequence[float], eps: float, tol: float = 1e-6) -> float:
    """Smallest delta at which the Bernstein upper bound on E[d] drops below eps."""
    if empirical_bernstein_upper(diffs, 1.0 - 1e-9) >= eps:
        return 1.0
    lo, hi = 1e-12, 1.0
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if empirical_bernstein_upper(diffs, mid) < eps:
            hi = mid
        else:
            lo = mid
    return hi


P_VALUES = {"bernstein": empirical_bernstein_p_value, "hoeffding": hoeffding_p_value}


@dataclass
class CalibrationResult:
    lam: float  # chosen knob (1.0 = original agent when nothing passes)
    eps: float
    delta: float
    n_tasks: int
    tested: list[tuple[float, float, float]]  # (lam, mean risk increase, p-value), in test order

    @property
    def guaranteed(self) -> bool:
        return self.lam < 1.0


def learn_then_test(
    lambdas: Sequence[float],
    losses: Callable[[float], Sequence[float]],
    baseline_losses: Sequence[float],
    eps: float = 0.02,
    delta: float = 0.1,
    test: str = "bernstein",
) -> CalibrationResult:
    """Fixed-sequence Learn-then-Test over ``lambdas`` (any order; sorted descending here).

    ``losses(lam)`` returns per-task losses (same task order as
    ``baseline_losses``, e.g. 1 - success).  Returns the smallest ``lam``
    such that every larger tested ``lam`` also passed.  ``test`` selects the
    p-value: ``bernstein`` (variance-adaptive, default) or ``hoeffding``.
    """
    p_value = P_VALUES[test]
    base = list(baseline_losses)
    chosen = 1.0
    tested: list[tuple[float, float, float]] = []
    for lam in sorted(set(lambdas), reverse=True):
        l = list(losses(lam))
        if len(l) != len(base):
            raise ValueError("losses(lam) must align with baseline_losses")
        diffs = [a - b for a, b in zip(l, base)]
        p = p_value(diffs, eps)
        tested.append((lam, sum(diffs) / len(diffs), p))
        if p > delta:
            break
        chosen = lam
    return CalibrationResult(chosen, eps, delta, len(base), tested)


def risk_curve(lambdas: Sequence[float], losses: Callable[[float], Sequence[float]], baseline_losses: Sequence[float]) -> list[tuple[float, float]]:
    base = list(baseline_losses)
    out = []
    for lam in sorted(set(lambdas)):
        l = list(losses(lam))
        out.append((lam, sum(a - b for a, b in zip(l, base)) / len(base)))
    return out
