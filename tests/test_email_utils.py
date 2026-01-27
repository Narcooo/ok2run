from agent_approval_gate.utils import extract_approval_id, truncate_email_reply


def test_extract_approval_id():
    text = "Please approve appr_123abc456def"
    assert extract_approval_id(text) == "appr_123abc456def"


def test_truncate_email_reply_quoted():
    body = "4 ok\n\nOn Tue, Someone wrote:\n> quoted"
    assert truncate_email_reply(body) == "4 ok"


def test_truncate_email_reply_signature():
    body = "2\n--\nSignature block"
    assert truncate_email_reply(body) == "2"
