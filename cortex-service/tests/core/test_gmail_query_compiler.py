from datetime import date
from app.core.gmail_query_compiler import compile_gmail_query
from app.core.operation_planner import GmailQueryConstraints

def test_compile_empty():
    assert compile_gmail_query({}) == ""

def test_compile_sender_recipient():
    constraints = {"sender": "Microsoft", "recipient": "John Doe"}
    query = compile_gmail_query(constraints)
    assert "from:(microsoft)" in query
    assert "to:(john doe)" in query

def test_compile_cc_bcc():
    constraints = {"cc": "team", "bcc": "boss"}
    query = compile_gmail_query(constraints)
    assert "cc:(team)" in query
    assert "bcc:(boss)" in query

def test_compile_booleans():
    constraints = {
        "unread": True,
        "read": True,
        "starred": True,
        "important": True,
        "inbox": True,
        "sent": True,
        "trash": True,
        "spam": True,
        "has_attachment": True,
    }
    query = compile_gmail_query(constraints)
    assert "is:unread" in query
    assert "is:read" in query
    assert "is:starred" in query
    assert "is:important" in query
    assert "in:inbox" in query
    assert "in:sent" in query
    assert "in:trash" in query
    assert "in:spam" in query
    assert "has:attachment" in query

def test_compile_text_fields():
    constraints = {
        "subject": "Interview",
        "keyword": "Job",
        "attachment_type": "pdf",
    }
    query = compile_gmail_query(constraints)
    assert "subject:(interview)" in query
    assert "job" in query
    assert "filename:(pdf)" in query

def test_compile_time_range():
    today = date(2026, 8, 10) # Monday
    
    q_today = compile_gmail_query({"time_range": "today"}, today_override=today)
    assert q_today == "after:2026/08/10"
    
    q_yesterday = compile_gmail_query({"time_range": "yesterday"}, today_override=today)
    assert q_yesterday == "after:2026/08/09 before:2026/08/10"
    
    q_this_week = compile_gmail_query({"time_range": "this_week"}, today_override=today)
    assert q_this_week == "after:2026/08/10"
    
    q_last_week = compile_gmail_query({"time_range": "last_week"}, today_override=today)
    assert q_last_week == "after:2026/08/03 before:2026/08/10"
    
    q_this_month = compile_gmail_query({"time_range": "this_month"}, today_override=today)
    assert q_this_month == "after:2026/08/01"
    
    q_last_month = compile_gmail_query({"time_range": "last_month"}, today_override=today)
    assert q_last_month == "after:2026/07/01 before:2026/08/01"

def test_compile_explicit_dates():
    constraints = {
        "after_date": "2026/01/01",
        "before_date": "2026/12/31",
    }
    query = compile_gmail_query(constraints)
    assert "after:2026/01/01" in query
    assert "before:2026/12/31" in query

def test_compile_with_pydantic_model():
    constraints = GmailQueryConstraints(sender="microsoft", time_range="today")
    today = date(2026, 8, 10)
    query = compile_gmail_query(constraints, today_override=today)
    assert query == "from:(microsoft) after:2026/08/10"
