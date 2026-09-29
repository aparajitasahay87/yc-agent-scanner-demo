from pydantic import BaseModel
from typing import Optional

class AgentContext(BaseModel):
    agent_id: str
    user_id: str
    tenant_id: str
    current_tenant: str  # For cross-tenant boundary validation
    intent: str

class ToolRequest(BaseModel):
    tool_name: str
    record_count: int = 1
    record_id: Optional[int] = None

class AuthorizationRequest(BaseModel):
    context: AgentContext
    action: ToolRequest