from gdopt.decision import OpenRouterJev


def _client(monkeypatch, response):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    j = OpenRouterJev()
    j._post = lambda questions, state: dict(response, _latency_s=0.1)  # type: ignore[method-assign]
    return j


def test_parse_noul_and_choice(monkeypatch):
    j = _client(monkeypatch, {"answers": {"q": {"type": "noul", "noul": 0.84}}, "usage": {"cost": 1.7e-05}})
    r = j.noul("q?", {"true": "t", "false": "f"}, {"x": 1})
    assert abs(r.probabilities["true"] - 0.84) < 1e-9 and abs(r.probabilities["false"] - 0.16) < 1e-9
    assert r.cost == 1.7e-05

    j = _client(monkeypatch, {"answers": {"q": {"type": "choice", "choice": "b", "probabilities": {"a": 0.2, "b": 0.8}}}, "usage": {"cost": 2e-05}})
    r = j.choice("q?", {"a": "A", "b": "B", "c": "C"}, {})
    assert r.top == "b" and r.probabilities["c"] == 0.0
