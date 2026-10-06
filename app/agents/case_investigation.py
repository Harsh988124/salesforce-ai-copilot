import os
import json
from typing import List, Union
from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

class CaseInvestigation(BaseModel):
    case_id: str = Field(default="Case", description="Case ID or Subject")
    insight: str = Field(description="1-sentence summary of the case problem and customer sentiment")
    action: str = Field(description="Specific action item for the Account Executive")

class CaseResponse(BaseModel):
    data: List[CaseInvestigation]

def investigate_cases(cases: Union[list, dict]) -> List[CaseInvestigation]:
    if not cases: return []
    case_list = cases if isinstance(cases, list) else [cases]
    
    prompt = f"Analyze these support cases: {json.dumps(case_list)}. For EACH case, evaluate the customer issue and derive specific actions."
    
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-super-120b-a12b",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"You are a Salesforce Support Copilot. Respond ONLY with valid JSON matching this schema: {json.dumps(CaseResponse.model_json_schema())}"},
            {"role": "user", "content": prompt}
        ]
    )
    result = CaseResponse(**json.loads(response.choices[0].message.content))
    return result.data