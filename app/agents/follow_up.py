import os
import json
from typing import List, Union
from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

class FollowUpAction(BaseModel):
    task_id: str = Field(default="Task", description="Task ID or Subject")
    recommendation: str = Field(description="Strategic recommendation for addressing this task")
    draft_message: str = Field(description="A ready-to-send draft email message")

class FollowUpResponse(BaseModel):
    data: List[FollowUpAction]

def generate_follow_ups(tasks: Union[list, dict]) -> List[FollowUpAction]:
    if not tasks: 
        return []
    task_list = tasks if isinstance(tasks, list) else [tasks]
    
    prompt = f"Analyze these CRM tasks: {json.dumps(task_list)}. Provide strategic recommendations and draft outreach emails."
    
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-super-120b-a12b",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"You are a Salesforce Productivity Copilot. Respond ONLY with valid JSON matching this schema: {json.dumps(FollowUpResponse.model_json_schema())}"},
            {"role": "user", "content": prompt}
        ]
    )
    result = FollowUpResponse(**json.loads(response.choices[0].message.content))
    return result.data