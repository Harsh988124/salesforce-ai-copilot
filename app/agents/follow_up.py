from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

class FollowUpAction(BaseModel):
    task_id: str
    subject: str
    due_date: str
    is_overdue: bool
    status: str
    recommendation: str
    draft_message: Optional[str] = None

def generate_follow_ups(customer_data: dict) -> List[FollowUpAction]:
    """
    Analyzes pending tasks, identifies overdue items, 
    and drafts suggested follow-up messages.
    """
    follow_ups = []
    tasks = customer_data.get("tasks", [])
    now = datetime.now(timezone.utc)

    for task in tasks:
        status = task.get("Status")
        # We only care about pending tasks
        if status == "Completed":
            continue

        due_date_str = task.get("ActivityDate")
        is_overdue = False
        recommendation = "Complete the task as scheduled."
        draft = None

        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if due_date < now:
                    is_overdue = True
                    recommendation = "High Priority: Task is overdue. Complete immediately or reschedule."
                    draft = f"Subject: Follow-up regarding {task.get('Subject', 'our last conversation')}\n\nHi there, I noticed we missed our target date for this. Just bubbling this up to see if we can resolve it today."
                else:
                    draft = f"Subject: Upcoming: {task.get('Subject', '')}\n\nHi, just getting ready for our upcoming touchpoint..."
            except ValueError:
                pass

        follow_ups.append(FollowUpAction(
            task_id=task.get("Id", "Unknown"),
            subject=task.get("Subject", "No Subject"),
            due_date=due_date_str or "No Due Date",
            is_overdue=is_overdue,
            status=status or "Unknown",
            recommendation=recommendation,
            draft_message=draft
        ))

    return follow_ups