from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone

class CaseInvestigation(BaseModel):
    case_id: str
    case_number: str
    summary: str
    duration_days: int
    missing_information: List[str]
    next_steps: List[str]
    escalation_recommended: bool

def investigate_cases(customer_data: dict) -> List[CaseInvestigation]:
    """
    Analyzes support cases to provide an investigation checklist, 
    flag missing data, and recommend escalation when justified.
    """
    investigations = []
    cases = customer_data.get("cases", [])
    now = datetime.now(timezone.utc)

    for case in cases:
        # Only investigate Open/New cases
        if case.get("Status") == "Closed":
            continue 

        missing_info = []
        next_steps = []
        escalation = False

        # 1. Calculate duration (Salesforce Datetime format is like 2026-10-02T12:00:00.000+0000)
        duration_days = 0
        created_date_str = case.get("CreatedDate")
        if created_date_str:
            try:
                # Safely extract just the YYYY-MM-DD part for a simple days calculation
                created_date = datetime.strptime(created_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                duration_days = (now - created_date).days
            except ValueError:
                pass

        # 2. Check for missing information
        if not case.get("Description"):
            missing_info.append("Case Description is empty.")
            next_steps.append("Contact the customer to request a detailed description of the issue.")
        
        # In Salesforce REST API, if a lookup field is empty, it usually returns None or isn't present
        if not case.get("ContactId"):
            missing_info.append("No primary Contact associated.")
            next_steps.append("Link a valid Contact to this case for communication tracking.")

        # 3. Evaluate escalation rules
        priority = case.get("Priority", "Low")
        if priority == "High" and duration_days >= 2:
            escalation = True
            next_steps.append("Escalate to Tier 2 Support: High priority case stalled for 2+ days.")
        elif duration_days >= 7:
            escalation = True
            next_steps.append("Escalate to Customer Success Manager: Case unresolved for over a week.")
        else:
            next_steps.append("Continue standard troubleshooting.")

        investigations.append(CaseInvestigation(
            case_id=case.get("Id", "Unknown"),
            case_number=case.get("CaseNumber", "Unknown"),
            summary=f"[{priority} Priority] {case.get('Subject', 'No Subject')}",
            duration_days=max(0, duration_days),
            missing_information=missing_info,
            next_steps=next_steps,
            escalation_recommended=escalation
        ))

    return investigations