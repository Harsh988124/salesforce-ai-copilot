import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from app.agents.case_investigation import investigate_cases

# Fixed mock date: Oct 2, 2026
MOCK_NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)

@pytest.fixture
def mock_dt():
    """Mocks datetime.now() to a fixed point in time."""
    with patch('app.agents.case_investigation.datetime') as mock_datetime:
        mock_datetime.now.return_value = MOCK_NOW
        mock_datetime.strptime.side_effect = lambda *args, **kw: datetime.strptime(*args, **kw)
        yield mock_datetime

def test_investigate_closed_case_ignored(mock_dt):
    """Test: Closed cases are not investigated."""
    data = {"cases": [{"Status": "Closed", "CaseNumber": "0001", "CreatedDate": "2026-10-01"}]}
    results = investigate_cases(data)
    assert len(results) == 0

def test_investigate_missing_info(mock_dt):
    """Test: Missing Description and ContactId are flagged."""
    data = {
        "cases": [{
            "Status": "New", 
            "Priority": "Low", 
            "CreatedDate": "2026-10-02T12:00:00.000+0000",
            "Subject": "Login Issue"
            # Explicitly missing Description and ContactId
        }]
    }
    results = investigate_cases(data)
    assert len(results) == 1
    assert "Case Description is empty." in results[0].missing_information
    assert "No primary Contact associated." in results[0].missing_information
    assert results[0].escalation_recommended is False

def test_high_priority_escalation(mock_dt):
    """Test: High priority case older than 2 days triggers Tier 2 escalation."""
    # Created 3 days ago (Sept 29)
    data = {
        "cases": [{
            "Status": "In Progress",
            "Priority": "High",
            "CreatedDate": "2026-09-29T10:00:00.000+0000",
            "Description": "Server down",
            "ContactId": "003A000001xyz"
        }]
    }
    results = investigate_cases(data)
    assert len(results) == 1
    assert results[0].escalation_recommended is True
    assert any("Tier 2 Support" in step for step in results[0].next_steps)

def test_duration_based_escalation(mock_dt):
    """Test: Any case open longer than 7 days triggers CSM escalation."""
    # Created 8 days ago (Sept 24)
    data = {
        "cases": [{
            "Status": "New",
            "Priority": "Low",
            "CreatedDate": "2026-09-24T15:00:00.000+0000",
            "Description": "General question",
            "ContactId": "003A000001xyz"
        }]
    }
    results = investigate_cases(data)
    assert len(results) == 1
    assert results[0].escalation_recommended is True
    assert any("Customer Success Manager" in step for step in results[0].next_steps)