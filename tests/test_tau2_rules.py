import json

from gdopt.adapters.tau2_rules import PolicyFacts


def _res(**kw):
    r = {"reservation_id": "R1", "user_id": "u", "origin": "JFK", "destination": "SFO", "flight_type": "one_way",
         "cabin": "economy", "flights": [{"flight_number": "HAT1", "date": "2024-05-20"}],
         "passengers": [{"first_name": "A"}], "created_at": "2024-05-01T10:00:00", "insurance": "no",
         "total_baggages": 2, "status": None}
    r.update(kw)
    return {"role": "tool", "id": "t1", "content": json.dumps(r)}


def _rules(facts, name, args):
    return {r for r, _ in facts.check(name, args)}


def test_cancel_ineligible_and_exemptions():
    f = PolicyFacts.from_messages([_res()])
    assert "cancel_ineligible" in _rules(f, "cancel_reservation", {"reservation_id": "R1"})
    for kw in ({"cabin": "business"}, {"insurance": "yes"}, {"created_at": "2024-05-15T09:00:00"}):
        assert not _rules(PolicyFacts.from_messages([_res(**kw)]), "cancel_reservation", {"reservation_id": "R1"})


def test_cancel_airline_cancelled_flight_is_allowed():
    msgs = [_res(), {"role": "assistant", "tool_calls": [{"id": "s", "name": "get_flight_status",
                                                         "arguments": {"flight_number": "HAT1", "date": "2024-05-20"}}]},
            {"role": "tool", "id": "s", "content": "cancelled"}]
    assert not _rules(PolicyFacts.from_messages(msgs), "cancel_reservation", {"reservation_id": "R1"})


def test_flown_bags_basic_economy():
    f = PolicyFacts.from_messages([_res(flights=[{"flight_number": "HAT1", "date": "2024-05-10"}])])
    assert _rules(f, "cancel_reservation", {"reservation_id": "R1"}) == {"cancel_flown"}
    f = PolicyFacts.from_messages([_res(cabin="basic_economy")])
    assert "modify_basic_economy" in _rules(f, "update_reservation_flights",
                                            {"reservation_id": "R1", "cabin": "basic_economy",
                                             "flights": [{"flight_number": "HAT9", "date": "2024-05-21"}]})
    assert "bag_remove" in _rules(f, "update_reservation_baggages", {"reservation_id": "R1", "total_baggages": 1})
