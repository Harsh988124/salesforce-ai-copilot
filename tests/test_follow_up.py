import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from app.agents.follow_up import generate_follow_ups

# Fixed mock date: Oct 3, 2026
MOCK_NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)

@pytest.fixture
def mock_dt():
    """Mocks datetime.now() to a fixed point in time."""
    with patch('app.agents.follow_up.datetime') as mock_datetime:
        mock_datetime.now.return_value = MOCK_NOW
        mock_datetime.strptime.side_effect = lambda *args, **kw: datetime.strptime(*args, **kw)
        yield mock_datetime

def test_completed_task_ignored(mock_dt):
    """Test: Completed tasks are skipped."""
    data = {"tasks": [{"Id": "1", "Status": "Completed"}]}
    results = generate_follow_ups(data)
    assert len(results) == 0

def test_overdue_task(mock_dt):
    """Test: Tasks with past due dates are flagged as overdue."""
    # Due Oct 1, checked on Oct 3
    data = {"tasks": [{"Id": "2", "Status": "Not Started", "ActivityDate": "2026-10-01", "Subject": "Email"}]}
    results = generate_follow_ups(data)
    assert len(results) == 1
    assert results[0].is_overdue is True
    assert "overdue" in results[0].recommendation

def test_future_task(mock_dt):
    """Test: Tasks with future due dates are not overdue."""
    # Due Oct 10, checked on Oct 3
    data = {"tasks": [{"Id": "3", "Status": "Not Started", "ActivityDate": "2026-10-10", "Subject": "Call"}]}
    results = generate_follow_ups(data)
    assert len(results) == 1
    assert results[0].is_overdue is False
    assert "Upcoming" in results[0].draft_message