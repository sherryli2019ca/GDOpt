import json

from gdopt.adapters.tau2 import load_results
from gdopt.profile import candidate_tiers, fit_situations, profile, split_by_trial
from gdopt.situation import SituationTree
from gdopt.toy import ToyRunner, make_llm_policy, make_tasks


def test_tree_partitions_and_reduces_entropy():
    X = [{"a": str(i % 2), "b": str(i % 3)} for i in range(200)]
    y = ["t" if i % 2 == 0 else "m" for i in range(200)]
    tree = SituationTree(max_depth=3, min_leaf=10).fit(X, y)
    leaves = tree.leaves()
    assert sum(l.n for l in leaves) == 200
    assert tree.root.split_feature == "a"
    assert all(len(l.counts) == 1 for l in leaves)
    assert tree.leaf({"a": "0", "b": "zzz"}).majority == "t"  # unseen value falls to default child


def test_profile_on_toy_traces():
    tasks = make_tasks(30, seed=1)
    runner = ToyRunner(tasks)
    trajs = [runner.trajectory(t.id, make_llm_policy(seed=100 * trial + i), trial=trial) for trial in range(4) for i, t in enumerate(tasks)]
    train, test = split_by_trial(trajs, [0, 1])
    model = fit_situations(train, max_depth=5, min_leaf=10)
    rep = profile(model, train, test)
    assert rep.n_steps_test == sum(t.n_steps for t in test)
    assert abs(sum(s.cost_share for s in rep.situations) - 1.0) < 1e-6
    assert 0 < rep.closed_tool_step_rate < 1
    cands = candidate_tiers(rep, code_min_test=5)
    assert set(cands.values()) <= {"code", "jev", "llm"}
    # The deterministic read-only lookup after the user gives the flight is a code candidate.
    assert "code" in cands.values()


def test_tau2_adapter(tmp_path):
    data = {
        "info": {"agent_info": {"llm": "x"}, "user_info": {"llm": "y"}, "num_trials": 1},
        "tasks": [{"id": "1"}],
        "simulations": [
            {
                "id": "s1", "task_id": "1", "trial": 0, "agent_cost": 0.01,
                "reward_info": {"reward": 1.0},
                "messages": [
                    {"role": "assistant", "content": "Hi!", "cost": 0.0, "usage": {"prompt_tokens": 10, "completion_tokens": 2}},
                    {"role": "user", "content": "cancel H8Q05L"},
                    {"role": "assistant", "tool_calls": [{"id": "c1", "name": "get_reservation_details", "arguments": {"reservation_id": "H8Q05L"}}], "cost": 0.002, "usage": {"prompt_tokens": 100, "completion_tokens": 20}},
                    {"role": "tool", "id": "c1", "content": "{\"status\": \"active\"}", "requestor": "assistant", "error": False},
                    {"role": "assistant", "content": "done", "cost": 0.001},
                ],
            }
        ],
    }
    p = tmp_path / "r.json"
    p.write_text(json.dumps(data))
    trajs = load_results(p)
    assert len(trajs) == 1 and trajs[0].success and trajs[0].n_steps == 3
    steps = list(trajs[0].steps())
    assert steps[1].action == "tool:get_reservation_details" and steps[1].cost == 0.002
    assert trajs[0].messages[3].tool_name == "get_reservation_details"
