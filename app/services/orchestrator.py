from pydantic import BaseModel
from typing import List
from app.agents.customer_insights import analyze_customer_360, Insight
from app.agents.case_investigation import investigate_cases, CaseInvestigation
from app.agents.sales_agent import analyze_sales, SalesAnalysis
from app.agents.follow_up import generate_follow_ups, FollowUpAction

class CopilotResponse(BaseModel):
    account_id: str
    status: str
    insights: List[Insight]
    case_investigations: List[CaseInvestigation] = []
    sales_analyses: List[SalesAnalysis] = []
    follow_ups: List[FollowUpAction] = []  # <--- New field added

def run_copilot(account_id: str, customer_data: dict) -> CopilotResponse:
    """
    Central orchestrator for the Copilot.
    Routes data to specialized agents and compiles a unified response.
    """
    # 1. Run the Customer Insights Agent
    insights = analyze_customer_360(customer_data)
    
    # 2. Run the Case Investigation Agent
    investigations = investigate_cases(customer_data)
    
    # 3. Run the Sales Agent
    sales_data = analyze_sales(customer_data)
    
    # 4. Run the Follow-up Agent
    follow_ups_data = generate_follow_ups(customer_data)
    
    # 5. Compile and return the unified response
    return CopilotResponse(
        account_id=account_id,
        status="SUCCESS",
        insights=insights,
        case_investigations=investigations,
        sales_analyses=sales_data,
        follow_ups=follow_ups_data
    )