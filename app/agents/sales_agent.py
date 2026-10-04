from pydantic import BaseModel
from typing import List

class SalesAnalysis(BaseModel):
    opportunity_id: str
    opportunity_name: str
    stage: str
    amount: float
    milestone: str
    missing_follow_up: bool
    suggested_action: str

def analyze_sales(customer_data: dict) -> List[SalesAnalysis]:
    """
    Analyzes open opportunities to summarize sales context, 
    flag missing follow-ups, and suggest next steps.
    """
    analyses = []
    opportunities = customer_data.get("opportunities", [])

    for opp in opportunities:
        # We only analyze active deals
        if opp.get("IsClosed"):
            continue
        
        # In Salesforce, NextStep is a standard field used to track follow-ups
        next_step = opp.get("NextStep")
        missing_follow_up = not bool(next_step)
        
        stage = opp.get("StageName", "Unknown Stage")
        amount = opp.get("Amount") or 0.0
        
        # Determine milestone based on typical Salesforce stages
        milestone = f"Currently in {stage}"
        if stage in ["Negotiation/Review", "Proposal/Price Quote"]:
            milestone = "Late stage - High priority for closure"
            
        # Formulate suggested action
        if missing_follow_up:
            if stage == "Negotiation/Review":
                suggested = "Schedule a closing call immediately. No next step defined."
            else:
                suggested = "Define a clear next step to move the deal forward."
        else:
            suggested = f"Execute planned next step: {next_step}"

        analyses.append(SalesAnalysis(
            opportunity_id=opp.get("Id", "Unknown"),
            opportunity_name=opp.get("Name", "Unknown"),
            stage=stage,
            amount=float(amount),
            milestone=milestone,
            missing_follow_up=missing_follow_up,
            suggested_action=suggested
        ))

    return analyses