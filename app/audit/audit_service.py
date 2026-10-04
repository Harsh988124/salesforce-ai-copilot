import logging
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

# Setup a dedicated logger for audit events
audit_logger = logging.getLogger("copilot.audit")
audit_logger.setLevel(logging.INFO)

class AuditEvent(BaseModel):
    action_id: str
    action_type: str
    target_object: str
    record_id: Optional[str]
    proposed_changes: Dict[str, Any]
    approval_status: str
    execution_status: str
    timestamp: str

# In-memory storage for local development
_AUDIT_LOGS: List[AuditEvent] = []

def record_audit_event(
    action_id: str,
    action_type: str,
    target_object: str,
    record_id: Optional[str],
    proposed_changes: Dict[str, Any],
    approval_status: str,
    execution_status: str
) -> AuditEvent:
    """Creates a secure audit record for any attempted Salesforce modification."""
    event = AuditEvent(
        action_id=action_id,
        action_type=action_type,
        target_object=target_object,
        record_id=record_id,
        proposed_changes=proposed_changes,
        approval_status=approval_status,
        execution_status=execution_status,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    _AUDIT_LOGS.append(event)
    audit_logger.info(f"AUDIT LOG: {event.model_dump_json()}")
    return event

def get_audit_logs() -> List[AuditEvent]:
    """Retrieves all recorded audit events."""
    return _AUDIT_LOGS