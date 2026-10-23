from gdopt.decision import FunctionDecisionModel, action_menu
from gdopt.local_eval import gold_hit, local_eval_markdown, local_evaluate
from gdopt.profile import fit_situations, split_by_trial
from gdopt.shadow import shadow_evaluate
from gdopt.toy import TOOLS, ToyRunner, ideal_action, make_llm_policy, make_tasks, simulated_decision_model
from gdopt.trace import all_steps


def test_gold_hit_rules():
    gold = [("cancel_reservation", {"reservation_id": "ABC123"}), ("get_user_details", {"user_id": "u_1"})]
    assert gold_hit("cancel_reservation", {"reservation_id": "ABC123"}, gold, []) is True
    assert gold_hit("cancel_reservation", {"reservation_id": "XXX"}, gold, []) is False
    assert gold_hit("cancel_reservation", None, gold, []) is False
    assert gold_hit("search_flights", {"x": 1}, gold, []) is None  # not a reference action
    # already executed -> not a hit again
    assert gold_hit("cancel_reservation", {"reservation_id": "ABC123"}, gold, [("cancel_reservation", {"reservation_id": "ABC123"})]) is False


def test_local_evaluate_on_toy():
    tasks = make_tasks(30, seed=2)
    runner = ToyRunner(tasks)
    trajs = [runner.trajectory(t.id, make_llm_policy(seed=10 * k + i), trial=k) for k in range(4) for i, t in enumerate(tasks)]
    train, test = split_by_trial(trajs, [0, 1])
    model = fit_situations(train, max_depth=4, min_leaf=10)
    # gold: for cancel tasks the reference is cancel_reservation(reservation_id)
    gold = {t.id: ([("cancel_reservation", {"reservation_id": t.reservation_id})] if t.kind == "cancel" else []) for t in tasks}
    jev = simulated_decision_model(accuracy=0.9, seed=3)
    shadow = shadow_evaluate(all_steps(test), model, jev, action_menu(TOOLS))
    rep = local_evaluate(shadow, test, model, gold)
    assert rep.n == shadow.records.__len__() and 0.5 < rep.agreement <= 1.0
    assert sum(rep.verdicts.values()) == rep.n
    assert set(rep.verdicts) <= {"agree", "jev_right", "llm_right", "neither", "undecidable"}
    md = local_eval_markdown(rep, {s.leaf_id: "r" for s in rep.situations})
    assert "Coverage curve" in md and "Per situation" in md


def test_tool_coverage_and_cost_aware_tier_table():
    from gdopt.shadow import ShadowRecord, ShadowResult

    recs = [ShadowRecord("t", i, 1, "message", {"message": 0.95, "tool:a": 0.05}, 0.0) for i in range(8)]
    recs += [ShadowRecord("t", 10 + i, 1, "tool:a", {"message": 0.05, "tool:a": 0.95}, 0.0) for i in range(2)]
    sh = ShadowResult(recs, 0.0).by_situation()[1]
    assert sh.agreement == 1.0
    assert abs(sh.tool_coverage[0.9] - 0.2) < 1e-9  # only the 2 confident tool decisions skip the LLM
    assert abs(sh.coverage_curve[0.9][1] - 1.0) < 1e-9
