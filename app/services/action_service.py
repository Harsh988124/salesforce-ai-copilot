import uuid
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from app.salesforce_client import create_salesforce_record

from app.audit.audit_service import record_audit_event

class ActionRequest(BaseModel):
    action_type: str  # 'CREATE' or 'UPDATE'
    target_object: str  # e.g., 'Task', 'Case', 'Opportunity'
    proposed_changes: Dict[str, Any]
    record_id: Optional[str] = None

class ActionProposal(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str
    target_object: str
    record_id: Optional[str] = None
    proposed_changes: Dict[str, Any]
    status: str = "PENDING"  # Workflow: PENDING -> APPROVED -> EXECUTED (or REJECTED)
    
# In-memory store for local development (will be replaced by DB in production)
_ACTION_STORE: Dict[str, ActionProposal] = {}

def propose_action(request: ActionRequest) -> ActionProposal:
    """Creates a new action proposal and holds it in PENDING state."""
    proposal = ActionProposal(
        action_type=request.action_type,
        target_object=request.target_object,
        record_id=request.record_id,
        proposed_changes=request.proposed_changes
    )
    _ACTION_STORE[proposal.action_id] = proposal
    return proposal

def get_action(action_id: str) -> Optional[ActionProposal]:
    """Retrieves a proposed action by ID."""
    return _ACTION_STORE.get(action_id)

def approve_action(action_id: str) -> Optional[ActionProposal]:
    """Transitions a PENDING action to APPROVED."""
    action = _ACTION_STORE.get(action_id)
    if action and action.status == "PENDING":
        action.status = "APPROVED"
    return action

def execute_action(action_id: str, access_token: str, instance_url: str) -> Optional[ActionProposal]:
    """
    Executes an APPROVED action against the live Salesforce org.
    """
    action = _ACTION_STORE.get(action_id)
    if not action:
        return None
    
    # 1. Strict Security Gate: Must be explicitly APPROVED
    if action.status != "APPROVED":
        raise ValueError("Action must be in APPROVED state before execution.")
    
    # 2. Execute the operation
    if action.action_type == "CREATE":
        sf_response = create_salesforce_record(
            access_token=access_token,
            instance_url=instance_url,
            object_name=action.target_object,
            data=action.proposed_changes
        )
        
        # 3. Update the state machine on success
        action.status = "EXECUTED"
        action.record_id = sf_response.get("id")  # Save the new Salesforce Record ID
        return action
    else:
        raise NotImplementedError("Only CREATE actions are currently supported for writes.")

def execute_action(action_id: str, access_token: str, instance_url: str) -> Optional[ActionProposal]:
    """
    Executes an APPROVED action against the live Salesforce org.
    """
    action = _ACTION_STORE.get(action_id)
    if not action:
        return None
    
    if action.status != "APPROVED":
        raise ValueError("Action must be in APPROVED state before execution.")
    
    try:
        if action.action_type == "CREATE":
            sf_response = create_salesforce_record(
                access_token=access_token,
                instance_url=instance_url,
                object_name=action.target_object,
                data=action.proposed_changes
            )
            
            action.status = "EXECUTED"
            action.record_id = sf_response.get("id")
            
            # ---> NEW: Record successful execution in the audit log
            record_audit_event(
                action_id=action.action_id,
                action_type=action.action_type,
                target_object=action.target_object,
                record_id=action.record_id,
                proposed_changes=action.proposed_changes,
                approval_status="APPROVED",
                execution_status="SUCCESS"
            )
            return action
        else:
            raise NotImplementedError("Only CREATE actions are currently supported for writes.")
            
    except Exception as e:
        # ---> NEW: Record failed execution in the audit log
        record_audit_event(
            action_id=action.action_id,
            action_type=action.action_type,
            target_object=action.target_object,
            record_id=None,
            proposed_changes=action.proposed_changes,
            approval_status="APPROVED",
            execution_status=f"FAILED: {str(e)}"
        )
        raise