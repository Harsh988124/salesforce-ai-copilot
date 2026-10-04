import pytest
from unittest.mock import patch
from app.services.action_service import (
    propose_action, approve_action, execute_action, 
    ActionRequest, _ACTION_STORE
)
from app.audit.audit_service import get_audit_logs, _AUDIT_LOGS

@pytest.fixture(autouse=True)
def reset_in_memory_stores():
    """Clears the global dictionaries/lists before each test runs."""
    _ACTION_STORE.clear()
    _AUDIT_LOGS.clear()

def test_propose_and_approve_action():
    """Test: Proposed actions start PENDING, then become APPROVED."""
    req = ActionRequest(
        action_type="CREATE", 
        target_object="Task", 
        proposed_changes={"Subject": "Test"}
    )
    action = propose_action(req)
    assert action.status == "PENDING"
    
    approved_action = approve_action(action.action_id)
    assert approved_action.status == "APPROVED"

def test_execute_unapproved_action_fails():
    """Test: The system blocks execution of PENDING actions."""
    req = ActionRequest(
        action_type="CREATE", 
        target_object="Task", 
        proposed_changes={"Subject": "Test"}
    )
    action = propose_action(req)
    
    # Expect a ValueError because we skipped the approve_action step
    with pytest.raises(ValueError, match="Action must be in APPROVED state"):
        execute_action(action.action_id, "mock_token", "mock_url")

@patch("app.services.action_service.create_salesforce_record")
def test_execute_approved_action_and_audit(mock_create):
    """Test: APPROVED actions execute successfully and generate an audit log."""
    # 1. Mock the Salesforce API response so we don't hit the real server
    mock_create.return_value = {"id": "00TMOCK12345678900"}
    
    # 2. Propose and Approve
    req = ActionRequest(
        action_type="CREATE", 
        target_object="Task", 
        proposed_changes={"Subject": "Test Task"}
    )
    action = propose_action(req)
    approve_action(action.action_id)
    
    # 3. Execute
    executed_action = execute_action(action.action_id, "mock_token", "mock_url")
    
    # 4. Verify Execution Status
    assert executed_action.status == "EXECUTED"
    assert executed_action.record_id == "00TMOCK12345678900"
    
    # 5. Verify Audit Log was created
    logs = get_audit_logs()
    assert len(logs) == 1
    assert logs[0].action_id == action.action_id
    assert logs[0].execution_status == "SUCCESS"
    assert logs[0].record_id == "00TMOCK12345678900"