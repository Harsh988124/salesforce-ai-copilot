from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

# Structured output schema for our insights
class Insight(BaseModel):
    type: str  # 'RISK', 'OPPORTUNITY', 'ACTION_REQUIRED'
    priority: str  # 'HIGH', 'MEDIUM', 'LOW'
    title: str
    description: str
    recommended_action: str
    relevant_record_id: Optional[str] = None
    supporting_evidence: Optional[Dict[str, Any]] = None

def analyze_customer_360(customer_data: dict) -> List[Insight]:
    """
    Analyzes Customer 360 data and returns structured insights.
    Currently uses deterministic rules as a reliable baseline before LLM integration.
    """
    insights = []
    now = datetime.now(timezone.utc)

    # 1. Identify High-priority unresolved support cases
    cases = customer_data.get("cases", [])
    for case in cases:
        status = case.get("Status")
        priority = case.get("Priority")
        if status != "Closed" and priority == "High":
            insights.append(Insight(
                type="RISK",
                priority="HIGH",
                title=f"High Priority Unresolved Case: {case.get('CaseNumber')}",
                description=case.get("Subject", "No subject provided"),
                recommended_action="Investigate and escalate if necessary.",
                relevant_record_id=case.get("Id"),
                supporting_evidence={"status": status, "priority": priority}
            ))

    # 2. Identify Opportunities closing within 14 days
    opportunities = customer_data.get("opportunities", [])
    for opp in opportunities:
        close_date_str = opp.get("CloseDate")
        if close_date_str and not opp.get("IsClosed"):
            try:
                # Salesforce returns YYYY-MM-DD for Date fields
                close_date = datetime.strptime(close_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_until_close = (close_date - now).days
                
                if 0 <= days_until_close <= 14:
                    priority = "HIGH" if days_until_close <= 7 else "MEDIUM"
                    insights.append(Insight(
                        type="OPPORTUNITY",
                        priority=priority,
                        title=f"Opportunity Closing Soon: {opp.get('Name')}",
                        description=f"Closing in {days_until_close} days. Amount: {opp.get('Amount', 'Unknown')}",
                        recommended_action="Follow up with the primary contact to secure the deal.",
                        relevant_record_id=opp.get("Id"),
                        supporting_evidence={"close_date": close_date_str, "amount": opp.get("Amount")}
                    ))
            except ValueError:
                pass  # Safely ignore malformed dates for now

    # 3. Identify Overdue unfinished tasks
    tasks = customer_data.get("tasks", [])
    for task in tasks:
        due_date_str = task.get("ActivityDate")
        if due_date_str and task.get("Status") != "Completed":
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if due_date < now:
                    insights.append(Insight(
                        type="ACTION_REQUIRED",
                        priority="MEDIUM",
                        title=f"Overdue Task: {task.get('Subject')}",
                        description=f"Task was due on {due_date_str}.",
                        recommended_action="Complete the task or reschedule.",
                        relevant_record_id=task.get("Id"),
                        supporting_evidence={"due_date": due_date_str, "status": task.get("Status")}
                    ))
            except ValueError:
                pass

    return insights