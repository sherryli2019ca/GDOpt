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


def test_retail_consistency_checks():
    import json
    from gdopt.adapters.tau2_retail_rules import RetailConsistencyChecker
    order = {"order_id": "#W1", "user_id": "u", "status": "pending (item modified)", "items": [
        {"name": "Lamp", "product_id": "p1", "item_id": "i1", "price": 10.0}], "payment_history": [
        {"transaction_type": "payment", "amount": 10.0, "payment_method_id": "credit_card_1"}]}
    product = {"name": "Lamp", "product_id": "p1", "variants": {
        "i1": {"item_id": "i1", "available": True, "options": {}, "price": 10.0},
        "i2": {"item_id": "i2", "available": False, "options": {}, "price": 9.0}}}
    msgs = [{"role": "user", "content": "I ordered it by mistake, please cancel"},
            {"role": "tool", "content": json.dumps(order)}, {"role": "tool", "content": json.dumps(product)}]
    c = RetailConsistencyChecker(msgs)
    call = {"role": "assistant", "tool_calls": [{"name": "cancel_pending_order",
                                                  "arguments": {"order_id": "#W1", "reason": "no longer needed"}}]}
    assert {r for r, _, _ in c.check(call)} == {"status_precondition", "cancel_reason"}
    assert [r for r, _, _ in c.check({"role": "assistant", "content": "There are 2 lamp options."})] == ["option_count"]
    assert [r for r, _, _ in c.check({"role": "assistant", "content": "$10.00 - $9.00 = $2.00 back"})] == ["arithmetic"]
    assert c.check({"role": "assistant", "content": "$10.00 - $9.00 = $1.00 back"}) == []
