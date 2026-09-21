from typing import Literal, Any
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str

class ApprovalAction(BaseModel):
    name: str
    arguments: dict[str, Any]
    description: str | None = None

class ChatRequest(BaseModel):
    thread_id: str = Field(
        min_length=1,
        max_length=100
    )

    message: str = Field(
        min_length=1,
        max_length=4000
    )

class ChatResponse(BaseModel):
    request_id: str
    thread_id: str
    status: Literal["completed", "approval_required"]
    response: str | None = None
    approval: (ApprovalAction | None) = None

class ApprovalDecisionRequest(BaseModel):
    decision: Literal[
        "approve",
        "reject"
    ]
    message: str | None = None