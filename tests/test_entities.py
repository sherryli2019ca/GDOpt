from gdopt.entities import EntitySchema, argument_closure, build_entity_table, learn_shape
from gdopt.trace import Message, ToolCall, Trajectory


def test_learn_shape_fine_and_coarse():
    fine = learn_shape(["sophia_silva_7557", "mia_li_3668", "raj_kumar_1234"])
    assert fine is not None and fine.find("my id is mia_li_3668 ok") == ["mia_li_3668"]
    coarse = learn_shape(["H8Q05L", "3ZQ1LD", "ABC123", "Q9Q9Q9"])
    assert coarse is not None and coarse.pattern == "[A-Z0-9]{6}"
    assert coarse.find("reservation H8Q05L please") == ["H8Q05L"]
    assert learn_shape(["please cancel", "refund me", "hello there"]) is None  # free text
    assert learn_shape(["yes", "no", "maybe", "ok"]) is None  # plain words


def _traj():
    msgs = [
        Message("user", content="Hi, my user id is sophia_silva_7557 and reservation H8Q05L."),
        Message("assistant", tool_calls=[ToolCall("get_reservation_details", {"reservation_id": "H8Q05L"})]),
        Message("tool", content='{"reservation_id": "H8Q05L", "user_id": "sophia_silva_7557", "flights": [{"flight_number": "HAT268"}]}', tool_name="get_reservation_details"),
        Message("assistant", tool_calls=[ToolCall("get_flight_status", {"flight_number": "HAT268", "date": "2024-05-24"})]),
    ]
    return Trajectory("t", "1", msgs, True)


def test_entity_table_and_closure():
    t = _traj()
    # Make the corpus big enough for shapes to be learned.
    corpus = [t] + [
        Trajectory(
            f"x{i}", "1",
            [Message("assistant", tool_calls=[ToolCall("get_reservation_details", {"reservation_id": r})]),
             Message("tool", content=f'{{"reservation_id": "{r}", "user_id": "{u}"}}', tool_name="get_reservation_details")],
            True,
        )
        for i, (r, u) in enumerate([("3ZQ1LD", "mia_li_3668"), ("ABC123", "raj_kumar_1234"), ("Q9Q9Q9", "ana_cruz_9999")])
    ]
    schema = EntitySchema.from_trajectories(corpus)
    assert "reservation_id" in schema.shapes and "user_id" in schema.shapes
    table = build_entity_table(t.messages[:1], schema)
    assert table.latest("reservation_id") == "H8Q05L" and table.latest("user_id") == "sophia_silva_7557"
    closure = argument_closure({"reservation_id": "H8Q05L"}, table)
    assert closure == {"reservation_id": "reservation_id"}
    table3 = build_entity_table(t.messages[:3], schema)
    closure2 = argument_closure({"flight_number": "HAT268", "date": "2024-05-24"}, table3)
    assert closure2["flight_number"] == "flight_number" and closure2["date"] is None


def test_coarse_shape_tolerates_ids_without_digits():
    from gdopt.entities import learn_shape

    ids = ["H8Q05L", "3ZQ1LD", "IFOYYZ", "NQNU5R", "M20IZO", "N6F783", "ABCDEF", "Q69X3R", "S5IK51", "OUEA45"]
    shape = learn_shape(ids)
    assert shape is not None and shape.pattern == "[A-Z0-9]{6}"
    assert shape.find("It's actually M20IZO, not N6F783.") == ["M20IZO", "N6F783"]


def test_coarse_shape_rejects_plain_words():
    from gdopt.entities import learn_shape

    assert learn_shape(["HELLO", "WORLD", "FLIGHT", "PLEASE", "CANCEL", "REFUND"]) is None
