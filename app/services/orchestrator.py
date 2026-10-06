from pydantic import BaseModel
from typing import List
from app.agents.customer_insights import analyze_customer_360, Insight
from app.agents.case_investigation import investigate_cases, CaseInvestigation
from app.agents.sales_agent import evaluate_opportunities, OpportunityAction
from app.agents.follow_up import generate_follow_ups, FollowUpAction

class CopilotResponse(BaseModel):
    account_id: str
    status: str
    insights: List[Insight]
    case_investigations: List[CaseInvestigation] = []
    sales_analyses: List[OpportunityAction] = []
    follow_ups: List[FollowUpAction] = []

def run_copilot(account_id: str, customer_data: dict) -> CopilotResponse:
    print("\n" + "="*50)
    print("🚀 RUNNING NEW GEMINI AI ORCHESTRATOR 🚀")
    print("="*50 + "\n")
    
    account_info = customer_data.get("account", {})
    cases = customer_data.get("cases", [])
    opportunities = customer_data.get("opportunities", [])
    tasks = customer_data.get("tasks", [])

    insight_obj = analyze_customer_360(account_info, cases, opportunities, tasks)
    investigations = investigate_cases(cases)
    sales_data = evaluate_opportunities(opportunities)
    follow_ups_data = generate_follow_ups(tasks)

   # 1. Create the response object FIRST
    final_response = CopilotResponse(
        account_id=account_id,
        status="SUCCESS",
        insights=[insight_obj],
        case_investigations=investigations,
        sales_analyses=sales_data,
        follow_ups=follow_ups_data
    )
    
    # 2. THEN print it
    print(final_response.model_dump_json(indent=2))
    
    return final_response