from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel

class SecurityRule(BaseModel):
    role: str
    allowed_tools: List[str]
    max_rows: Optional[int] = None
    enforce_tenant_match: bool = True

class YCAgentScanner:
    def __init__(self, policies: List[SecurityRule]):
        self.policies = {rule.role: rule for rule in policies}

    def _evaluate_token_exchange(self, body: dict) -> JSONResponse | None:
        """Evaluates RFC 8693 token exchange claims against runtime intent."""
        token_claims = body.get("token_claims", {})
        tool_call = body.get("tool_call", {})

        # Extract Delegated Actor context (RFC 8693)
        acting_agent = token_claims.get("act", {}).get("client_id", "unknown")
        agent_role = token_claims.get("act", {}).get("role", "unknown")
        session_tenant = token_claims.get("tenant", "")
        
        # Extract Execution Intent
        tool = tool_call.get("tool", "")
        rows_requested = tool_call.get("rows_requested", 0)
        target_tenant = tool_call.get("tenant_context", "")

        rule = self.policies.get(agent_role)

        # 1. Role / Tool Authorization Check
        if not rule or tool not in rule.allowed_tools:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": "DENIED",
                    "error_code": "UNAUTHORIZED_TOOL_FOR_ROLE",
                    "message": f"Agent '{acting_agent}' (Role: {agent_role}) is not authorized to execute '{tool}'."
                }
            )

        # 2. Scope / Row Limit Check (Stops 1,000,000 row bulk exports)
        if rule.max_rows and rows_requested > rule.max_rows:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": "DENIED",
                    "error_code": "SCOPE_ROW_LIMIT_EXCEEDED",
                    "message": f"Bulk export blocked. Requested {rows_requested} rows; {agent_role} limited to {rule.max_rows}."
                }
            )

        # 3. Tenant Boundary Check (Cross-tenant leak prevention)
        if rule.enforce_tenant_match and session_tenant != target_tenant:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "intent_mismatch_correction_required",
                    "error_code": "TENANT_MISMATCH",
                    "message": f"Session is bound to tenant '{session_tenant}', but tool targeted '{target_tenant}'. Please self-correct."
                }
            )
            
        return None  # Passed all checks

    def fastapi_middleware(self):
        """Returns an ASGI middleware function to drop into FastAPI."""
        async def middleware(request: Request, call_next):
            if request.method == "POST" and "/api/agent/tool-call" in request.url.path:
                try:
                    body = await request.json()
                except Exception:
                    return JSONResponse(status_code=400, content={"error": "Invalid payload"})
                
                violation_response = self._evaluate_token_exchange(body)
                if violation_response:
                    return violation_response
                    
            return await call_next(request)
        return middleware