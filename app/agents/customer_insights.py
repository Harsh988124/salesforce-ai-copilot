import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

class Insight(BaseModel):
    account_health: str = Field(description="Overall account status: Growing, Stable, At Risk, or Critical")
    churn_risk: str = Field(description="Churn risk level (High, Medium, Low) with brief explanation")
    executive_summary: str = Field(description="A 2-3 sentence strategic synthesis of the relationship and opportunities/risks")
    recommended_action: str = Field(description="The single most urgent strategic action for the AE")

def analyze_customer_360(account: dict, cases: list, opportunities: list, tasks: list) -> Insight:
    prompt = f"Analyze this customer data: {json.dumps({'account': account, 'cases': cases, 'opportunities': opportunities, 'tasks': tasks})}. Synthesize an executive summary, account health rating, churn risk assessment, and top recommended action."
    
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-super-120b-a12b",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"You are a Salesforce Copilot. Respond ONLY with valid JSON matching this schema: {json.dumps(Insight.model_json_schema())}"},
            {"role": "user", "content": prompt}
        ]
    )
    return Insight(**json.loads(response.choices[0].message.content))