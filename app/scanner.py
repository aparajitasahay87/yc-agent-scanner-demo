from datetime import datetime
from fastapi import HTTPException, status
from app.models import AuthorizationRequest
from app.database import DATABASE_STORE

def evaluate_agent_policy(req: AuthorizationRequest):
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    ctx = req.context
    act = req.action

    def make_audit(decision: str, policy_name: str, reason: str):
        return {
            "timestamp": timestamp,
            "agent_id": ctx.agent_id,
            "user_id": ctx.user_id,
            "tenant_id": ctx.tenant_id,
            "intent": ctx.intent,
            "tool": act.tool_name,
            "decision": decision,
            "policy": policy_name,
            "reason": reason
        }

    # --- Policy 3: Cross-Tenant Access Boundary ---
    if ctx.tenant_id != ctx.current_tenant:
        audit = make_audit("DENY", "CROSS_TENANT_ISOLATION", "TENANT_MISMATCH_VIOLATION")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Cross-tenant access violation detected.", "audit_record": audit}
        )

    # --- Database Record-Level Tenant Enforcement ---
    if act.record_id and act.record_id in DATABASE_STORE:
        record = DATABASE_STORE[act.record_id]
        if record["tenant"].lower() != ctx.tenant_id.lower():
            audit = make_audit("DENY", "RECORD_TENANT_ISOLATION", "UNAUTHORIZED_RECORD_OWNERSHIP")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": f"Tenant '{ctx.tenant_id}' attempted to access record owned by '{record['tenant']}'.", "audit_record": audit}
            )

   # --- Policy 2: Excessive / Bulk Access Boundary ---
    if act.tool_name == "customer_lookup" and act.record_count > 10:
        audit = make_audit("DENY", "EXCESSIVE_BULK_ACCESS", "VOLUME_THRESHOLD_EXCEEDED")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Excessive bulk access detected: max 10 records allowed for support role.",
                "audit_record": audit
            }
        )

    # --- Intent vs Action Alignment (Valid Token, Wrong Intent / Context Drift) ---
    if ctx.intent == "resolve_support_ticket" and act.tool_name == "export_all_customers":
        audit = make_audit("DENY", "SUPPORT_CUSTOMER_ACCESS", "INTENT_ACTION_MISMATCH")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Context drift detected. Tool execution prohibited for current task intent.", "audit_record": audit}
        )

    # --- Policy 1: Normal Access (Allowed) ---
    allowed_data = DATABASE_STORE.get(act.record_id, {"info": "Batch lookup allowed"})
    audit = make_audit("ALLOW", "SUPPORT_CUSTOMER_ACCESS", "VALIDATED_WITHIN_BOUNDS")
    
    return {
        "status": "ALLOW",
        "message": f"Action '{act.tool_name}' verified successfully.",
        "data": allowed_data,
        "audit_record": audit
    }