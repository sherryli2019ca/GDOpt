from gdopt.calibrate import empirical_bernstein_p_value, hoeffding_p_value, learn_then_test
from gdopt.decision import FunctionDecisionModel, action_menu
from gdopt.profile import fit_situations, profile, split_by_trial
from gdopt.replay import evaluate
from gdopt.tiers import Tier, TieredPolicy, TierTable, effective_tau
from gdopt.toy import POLICY_TEXT, TOOLS, ToyRunner, make_llm_policy, make_tasks, simulated_decision_model, tiered_as_policy


def test_ltt_picks_most_aggressive_safe_lambda():
    n = 1000
    base = [0.0] * n

    # risk increase grows as lam shrinks: lam=1 -> 0, lam=0.5 -> 0.01, lam=0.25 -> 0.15, lam=0 -> 0.2
    def losses(lam):
        k = int(round((1 - lam) * 0.2 * n)) if lam < 0.5 else int(round((1 - lam) * 0.02 * n))
        return [1.0] * k + [0.0] * (n - k)

    res = learn_then_test([0.0, 0.25, 0.5, 0.75, 1.0], losses, base, eps=0.05, delta=0.1)
    assert res.lam == 0.5 and res.guaranteed
    assert [l for l, _, _ in res.tested] == [1.0, 0.75, 0.5, 0.25]


def test_p_values():
    assert empirical_bernstein_p_value([0.0] * 1000, 0.05) < 0.01
    assert empirical_bernstein_p_value([0.0] * 50, 0.05) > 0.1  # too few tasks to certify
    assert empirical_bernstein_p_value([0.1] * 100, 0.05) == 1.0
    assert hoeffding_p_value([0.0] * 5000, 0.05) < 0.1
    assert hoeffding_p_value([0.1] * 100, 0.05) == 1.0
    # Bernstein is tighter than Hoeffding when the differences are mostly zero.
    d = [1.0] * 5 + [-1.0] * 5 + [0.0] * 490
    assert empirical_bernstein_p_value(d, 0.05) < hoeffding_p_value(d, 0.05)


def test_effective_tau_monotone():
    assert effective_tau(0.8, 0.0) == 0.8 and effective_tau(0.8, 1.0) == 1.0
    assert effective_tau(0.8, 0.5) == 0.9


def test_tiered_policy_end_to_end_on_toy():
    tasks = make_tasks(45, seed=3)
    runner = ToyRunner(tasks)
    llm = make_llm_policy(seed=7)
    trajs = [runner.trajectory(t.id, make_llm_policy(seed=1000 * trial + i), trial=trial) for trial in range(4) for i, t in enumerate(tasks)]
    train, test = split_by_trial(trajs, [0, 1])
    model = fit_situations(train, max_depth=5, min_leaf=10)
    rep = profile(model, train, test)
    table = TierTable.from_profile(rep, default_tau=0.7, code_min_test=5)
    assert table.counts()["llm"] < len(rep.situations)

    jev = simulated_decision_model(accuracy=0.97, seed=11)
    ids = [t.id for t in tasks]
    baseline = evaluate(runner, ids, llm)

    def make(lam):
        return tiered_as_policy(TieredPolicy(model, table, jev, llm, TOOLS, POLICY_TEXT, lam=lam))

    original = evaluate(runner, ids, make(1.0))
    assert original.llm_step_share == 1.0  # lam = 1 never leaves the LLM
    optimized = evaluate(runner, ids, make(0.0))
    assert optimized.llm_step_share < 1.0
    assert optimized.mean_cost < baseline.mean_cost
    assert optimized.success_rate >= baseline.success_rate - 0.1


def test_tiered_policy_falls_back_without_decision_model():
    tasks = make_tasks(6, seed=5)
    runner = ToyRunner(tasks)
    llm = make_llm_policy(seed=1)
    trajs = [runner.trajectory(t.id, llm, trial=k) for k in range(2) for t in tasks]
    model = fit_situations(trajs, max_depth=3, min_leaf=2)
    rep = profile(model, trajs, trajs)
    table = TierTable.from_profile(rep, code_min_test=1000)  # no code rules -> jev candidates only
    pol = TieredPolicy(model, table, None, llm, TOOLS, lam=0.0)
    d = pol.decide(trajs[0].messages[:1])
    assert d.tier_used == Tier.LLM and d.llm_called


def test_function_decision_model_normalizes():
    m = FunctionDecisionModel(lambda opts, state: {"tool:a": 3.0})
    r = m.choice("q", action_menu({"a": "x"}), {})
    assert set(r.probabilities) == {"message", "tool:a"} and abs(sum(r.probabilities.values()) - 1) < 1e-9
