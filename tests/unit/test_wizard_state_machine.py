from wizard_bot.wizard.state import back_step_local, push_step_local


def test_push_step_local_idempotent():
    assert push_step_local(["mode"], "mode") == ["mode"]


def test_push_step_local_appends():
    assert push_step_local(["mode"], "kind") == ["mode", "kind"]


def test_back_step_local_goes_one_step_back():
    history, active = back_step_local(["mode", "kind", "start_param"])
    assert history == ["mode", "kind"]
    assert active == "kind"
