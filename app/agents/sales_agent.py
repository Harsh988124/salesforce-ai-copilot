import os
import json
from typing import List, Union
from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

class OpportunityAction(BaseModel):
    opportunity_id: str = Field(default="Opportunity", description="Opportunity Name or ID")
    risk_level: str = Field(description="High, Medium, or Low risk level")
    insight: str = Field(description="1-sentence deal health assessment")
    action: str = Field(description="Specific next step to close or advance the deal")

class SalesResponse(BaseModel):
    data: List[OpportunityAction]

def evaluate_opportunities(opportunities: Union[list, dict]) -> List[OpportunityAction]:
    if not opportunities: 
        return []
    opp_list = opportunities if isinstance(opportunities, list) else [opportunities]
    
    prompt = f"Analyze these sales opportunities: {json.dumps(opp_list)}. Identify close date risks, bottlenecks, and the best next step."
    
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-super-120b-a12b",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"You are a Salesforce Revenue Copilot. Respond ONLY with valid JSON matching this schema: {json.dumps(SalesResponse.model_json_schema())}"},
            {"role": "user", "content": prompt}
        ]
    )
    result = SalesResponse(**json.loads(response.choices[0].message.content))
    return result.data