from gdopt.decision import FunctionDecisionModel, TwoStageDecisionModel, action_menu


def test_two_stage_combines_gate_and_choice():
    def fn(options, state):
        if set(options) == {"true", "false"}:
            return {"true": 0.8, "false": 0.2}
        return {"tool:a": 0.75, "tool:b": 0.25}

    m = TwoStageDecisionModel(FunctionDecisionModel(fn))
    r = m.choice("q", action_menu({"a": "A", "b": "B"}), {})
    assert abs(r.probabilities["message"] - 0.2) < 1e-9
    assert abs(r.probabilities["tool:a"] - 0.6) < 1e-9 and abs(r.probabilities["tool:b"] - 0.2) < 1e-9
    assert r.top == "tool:a" and m.inner.n_calls == 2


def test_two_stage_skips_choice_when_gate_is_low():
    def fn(options, state):
        return {"true": 0.01, "false": 0.99} if "true" in options else {"tool:a": 1.0}

    m = TwoStageDecisionModel(FunctionDecisionModel(fn))
    r = m.choice("q", action_menu({"a": "A", "b": "B"}), {})
    assert r.top == "message" and m.inner.n_calls == 1
