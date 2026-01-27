from agent_approval_gate.service import create_allow_rule, create_session_allow, get_allow_rule, get_session_allow


def test_allow_rule_match(db_session):
    client_id = "client-1"
    action_type = "exec_cmd"
    rule = create_allow_rule(db_session, client_id, action_type)
    found = get_allow_rule(db_session, client_id, action_type)
    assert found is not None
    assert found.rule_id == rule.rule_id


def test_session_allow_match(db_session):
    client_id = "client-1"
    session_id = "sess-1"
    action_type = "http_request"
    record = create_session_allow(db_session, client_id, session_id, action_type)
    found = get_session_allow(db_session, client_id, session_id, action_type)
    assert found is not None
    assert found.id == record.id
