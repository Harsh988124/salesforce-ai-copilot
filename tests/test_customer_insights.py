import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from app.agents.customer_insights import analyze_customer_360, Insight

# A fixed date for testing to ensure deterministic results
MOCK_NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)

@pytest.fixture
def mock_dt():
    """Mocks datetime.now() to a fixed point in time, while keeping strptime working."""
    with patch('app.agents.customer_insights.datetime') as mock_datetime:
        mock_datetime.now.return_value = MOCK_NOW
        mock_datetime.strptime.side_effect = lambda *args, **kw: datetime.strptime(*args, **kw)
        yield mock_datetime

def test_empty_customer_360(mock_dt):
    """Test: Empty Customer 360 data."""
    insights = analyze_customer_360({})
    assert len(insights) == 0

def test_high_priority_unresolved_case(mock_dt):
    """Test: High-priority unresolved case and Closed high-priority case."""
    data = {
        "cases": [
            {"Id": "5001", "CaseNumber": "0001", "Subject": "System Down", "Status": "New", "Priority": "High"},
            {"Id": "5002", "CaseNumber": "0002", "Subject": "Login Issue", "Status": "Closed", "Priority": "High"},
            {"Id": "5003", "CaseNumber": "0003", "Subject": "Billing", "Status": "New", "Priority": "Low"}
        ]
    }
    insights = analyze_customer_360(data)
    assert len(insights) == 1
    assert insights[0].type == "RISK"
    assert insights[0].priority == "HIGH"
    assert insights[0].relevant_record_id == "5001"

def test_opportunity_closing_within_14_days(mock_dt):
    """Test: Opportunities closing within 14 days, outside 14 days, and closed."""
    data = {
        "opportunities": [
            # Closes in 5 days -> HIGH (Oct 7 is 5 days from Oct 2 mock)
            {"Id": "0061", "Name": "Big Deal", "CloseDate": "2026-10-07", "IsClosed": False, "Amount": 10000},
            # Closes in 20 days -> No Insight (Oct 22)
            {"Id": "0062", "Name": "Future Deal", "CloseDate": "2026-10-22", "IsClosed": False, "Amount": 5000},
            # Already closed -> No Insight
            {"Id": "0063", "Name": "Won Deal", "CloseDate": "2026-10-01", "IsClosed": True, "Amount": 2000}
        ]
    }
    insights = analyze_customer_360(data)
    assert len(insights) == 1
    assert insights[0].type == "OPPORTUNITY"
    assert insights[0].priority == "HIGH"
    assert insights[0].relevant_record_id == "0061"

def test_overdue_unfinished_task(mock_dt):
    """Test: Overdue unfinished task and Completed task."""
    data = {
        "tasks": [
            # Due yesterday (Oct 1) -> Overdue
            {"Id": "00T1", "Subject": "Call client", "ActivityDate": "2026-10-01", "Status": "Not Started"},
            # Due yesterday but completed -> No Insight
            {"Id": "00T2", "Subject": "Email prep", "ActivityDate": "2026-10-01", "Status": "Completed"},
            # Due in the future -> No Insight
            {"Id": "00T3", "Subject": "Future sync", "ActivityDate": "2026-10-05", "Status": "Not Started"}
        ]
    }
    insights = analyze_customer_360(data)
    assert len(insights) == 1
    assert insights[0].type == "ACTION_REQUIRED"
    assert insights[0].priority == "MEDIUM"
    assert insights[0].relevant_record_id == "00T1"

def test_malformed_dates_ignored_safely(mock_dt):
    """Test: Missing or malformed dates do not crash the application."""
    data = {
        "opportunities": [{"Id": "0064", "Name": "Bad Date Deal", "CloseDate": "Not-A-Date", "IsClosed": False}]
    }
    insights = analyze_customer_360(data)
    assert len(insights) == 0

def test_multiple_simultaneous_insights(mock_dt):
    """Test: Multiple simultaneous insights."""
    data = {
        "cases": [{"Id": "5001", "CaseNumber": "0001", "Subject": "Down", "Status": "New", "Priority": "High"}],
        "opportunities": [{"Id": "0061", "Name": "Deal", "CloseDate": "2026-10-07", "IsClosed": False}],
        "tasks": [{"Id": "00T1", "Subject": "Call", "ActivityDate": "2026-10-01", "Status": "Not Started"}]
    }
    insights = analyze_customer_360(data)
    assert len(insights) == 3
    types = {i.type for i in insights}
    assert types == {"RISK", "OPPORTUNITY", "ACTION_REQUIRED"}