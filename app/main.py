# app/main.py
from fastapi import FastAPI, HTTPException
from app.models import AuthorizationRequest
from app.scanner import evaluate_agent_policy
from app.logger import log_audit_event

app = FastAPI(
    title="YC Agent PEP Security SDK",
    description="Deterministic runtime policy enforcement for autonomous AI agents.",
    version="1.0.0"
)

@app.post("/api/v1/enforce")
async def enforce_policy(req: AuthorizationRequest):
    try:
        # Evaluate policies
        result = evaluate_agent_policy(req)
        
        # Log ALLOW decision audit record
        if "audit_record" in result:
            log_audit_event(result["audit_record"])
            
        return result
        
    except HTTPException as exc:
        # Log DENY decision audit record from the 403 exception detail
        detail = exc.detail
        if isinstance(detail, dict) and "audit_record" in detail:
            log_audit_event(detail["audit_record"])
            
        raise exc

@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "active"}