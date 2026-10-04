import pytest
from app.agents.sales_agent import analyze_sales

def test_closed_opportunity_ignored():
    """Test: Closed opportunities are not analyzed."""
    data = {"opportunities": [{"Id": "1", "IsClosed": True, "StageName": "Closed Won"}]}
    results = analyze_sales(data)
    assert len(results) == 0

def test_missing_follow_up_flagged():
    """Test: Missing NextStep triggers a warning, especially in late stages."""
    data = {
        "opportunities": [{
            "Id": "2",
            "IsClosed": False,
            "StageName": "Negotiation/Review",
            "NextStep": None,
            "Amount": 10000
        }]
    }
    results = analyze_sales(data)
    assert len(results) == 1
    assert results[0].missing_follow_up is True
    assert "closing call immediately" in results[0].suggested_action

def test_existing_follow_up_recognized():
    """Test: Existing NextStep is recognized and logged as the suggested action."""
    data = {
        "opportunities": [{
            "Id": "3",
            "IsClosed": False,
            "StageName": "Prospecting",
            "NextStep": "Call client on Friday"
        }]
    }
    results = analyze_sales(data)
    assert len(results) == 1
    assert results[0].missing_follow_up is False
    assert "Call client on Friday" in results[0].suggested_action