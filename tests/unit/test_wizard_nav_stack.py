from wizard_bot.nav.stack import pop_local, push_local


def test_push_local_is_idempotent_for_same_route():
    assert push_local(["MAIN"], "MAIN") == ["MAIN"]


def test_push_local_appends_new_route():
    assert push_local(["MAIN"], "CAMPAIGNS_LIST") == ["MAIN", "CAMPAIGNS_LIST"]


def test_pop_local_returns_previous_route():
    stack, route = pop_local(["MAIN", "CAMPAIGNS_LIST"], "MAIN")
    assert stack == ["MAIN"]
    assert route == "MAIN"


def test_pop_local_fallback_when_empty():
    stack, route = pop_local([], "MAIN")
    assert stack == ["MAIN"]
    assert route == "MAIN"
