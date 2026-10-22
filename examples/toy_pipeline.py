"""End-to-end GDOpt on the toy environment (no API keys needed).

Steps: generate traces with the noisy "LLM" policy -> fit situations ->
profile -> tier table -> calibrate the global knob with Learn-then-Test on a
calibration split -> evaluate cost / success on a held-out split.
"""

from __future__ import annotations

from gdopt import TierTable, TieredPolicy, evaluate, fit_situations, learn_then_test, profile, risk_curve, split_by_trial
from gdopt.report import profile_markdown
from gdopt.toy import POLICY_TEXT, TOOLS, ToyRunner, make_llm_policy, make_tasks, simulated_decision_model, tiered_as_policy


def main() -> None:
    tasks = make_tasks(900, seed=0)
    runner = ToyRunner(tasks)
    llm = make_llm_policy(seed=42)

    # 1-2. traces -> situations -> profile
    trajs = [runner.trajectory(t.id, make_llm_policy(seed=1000 * trial + i), trial=trial) for trial in range(4) for i, t in enumerate(tasks)]
    train, test = split_by_trial(trajs, [0, 1])
    model = fit_situations(train, max_depth=5, min_leaf=10)
    rep = profile(model, train, test)
    print(profile_markdown(rep, title="Toy profile", code_min_test=5))

    # 4. tier table (no shadow stage here: the simulated Jev is used directly)
    table = TierTable.from_profile(rep, default_tau=0.7, code_min_test=5)
    print("tiers:", table.counts())
    jev = simulated_decision_model(accuracy=0.93, seed=1)

    # Certifying eps = 0.05 at delta = 0.1 needs a few hundred calibration tasks.
    calib_ids = [t.id for t in tasks[:600]]
    held_ids = [t.id for t in tasks[600:]]

    def tiered(lam: float):
        return tiered_as_policy(TieredPolicy(model, table, jev, llm, TOOLS, POLICY_TEXT, lam=lam))

    base_losses = evaluate(runner, calib_ids, llm).losses()
    lambdas = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    print("risk curve (lam, mean risk increase):", [(l, round(r, 3)) for l, r in risk_curve(lambdas, lambda lam: evaluate(runner, calib_ids, tiered(lam)).losses(), base_losses)])
    cal = learn_then_test(lambdas, lambda lam: evaluate(runner, calib_ids, tiered(lam)).losses(), base_losses, eps=0.05, delta=0.1)
    print(f"chosen lam = {cal.lam} (eps={cal.eps}, delta={cal.delta}); tested: {[(l, round(d, 3), round(p, 3)) for l, d, p in cal.tested]}")

    # 5. held-out evaluation
    base = evaluate(runner, held_ids, llm)
    opt = evaluate(runner, held_ids, tiered(cal.lam))
    print(f"baseline : success {base.success_rate:.3f}  cost/task ${base.mean_cost:.5f}  LLM-step share {base.llm_step_share:.2f}")
    print(f"optimized: success {opt.success_rate:.3f}  cost/task ${opt.mean_cost:.5f}  LLM-step share {opt.llm_step_share:.2f}")


if __name__ == "__main__":
    main()
