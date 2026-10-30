import hmac
import hashlib
import json
import os
import time
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional

app = FastAPI(title="YCAgentScanner PEP", version="1.0.0")

# Secret shared between Host Application and Scanner for task context signing
SECRET_KEY = os.environ.get("SCANNER_SIGNING_SECRET", "dev-only-signing-secret").encode("utf-8")

# The scanner is the only component holding the Booking API credential
BOOKING_API_URL = os.environ.get("BOOKING_API_URL", "http://127.0.0.1:8001")
BOOKING_API_KEY = os.environ.get("BOOKING_API_KEY", "dev-only-booking-key")

class ToolRequestPayload(BaseModel):
    task_context: Dict[str, Any]
    signature: str
    tool: str
    operation: str
    resource_id: Optional[str] = None

# Audit log storage in memory for the MVP
AUDIT_LOGS = []

def verify_signature(context: Dict[str, Any], signature: str) -> bool:
    """Verifies the HMAC-SHA256 signature of the host-signed task context."""
    try:
        # Canonicalize the context dictionary to a stable JSON string
        canonical_data = json.dumps(context, sort_keys=True).encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY, canonical_data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, signature)
    except Exception:
        return False

@app.post("/evaluate")
def evaluate_action(payload: ToolRequestPayload):
    start_time = time.time()
    
    # FAIL-CLOSED PRINCIPLE: Wrap evaluation in try/except; default to DENY on failure
    try:
        context = payload.task_context
        
        # 1. Verify Task Context Signature
        if not verify_signature(context, payload.signature):
            decision_record = create_audit_record(context, payload, "DENY", "INVALID_SIGNATURE", "Signature verification failed", start_time)
            AUDIT_LOGS.append(decision_record)
            return {"decision": "DENY", "reason": "INVALID_SIGNATURE"}

        intent = context.get("intent")
        allowed_tools = context.get("allowed_tools", [])
        resource_scope = context.get("resource_scope", {})
        
        # 2. Check if tool is allowed for this intent / task
        if payload.tool not in allowed_tools:
            decision_record = create_audit_record(context, payload, "DENY", "TOOL_NOT_ALLOWED", f"Tool {payload.tool} not permitted for intent {intent}", start_time)
            AUDIT_LOGS.append(decision_record)
            return {"decision": "DENY", "reason": "TOOL_NOT_ALLOWED"}

        # 3. Task-Specific Policy Evaluation (The core Gym-Booking logic)
        if payload.tool == "booking" and payload.operation == "cancel":
            allowed_reservations = resource_scope.get("reservation_ids", [])
            
            # Check if requested resource falls within the trusted task resource scope
            if payload.resource_id not in allowed_reservations:
                decision_record = create_audit_record(context, payload, "DENY", "ACTION_OUTSIDE_TASK_SCOPE", f"Resource {payload.resource_id} is outside task scope", start_time)
                AUDIT_LOGS.append(decision_record)
                return {"decision": "DENY", "reason": "ACTION_OUTSIDE_TASK_SCOPE"}
            
            # If intent does not permit cancellation (e.g., book_class task)
            if intent == "book_class":
                decision_record = create_audit_record(context, payload, "DENY", "ACTION_OUTSIDE_TASK_SCOPE", "Cancellation not permitted under book_class intent", start_time)
                AUDIT_LOGS.append(decision_record)
                return {"decision": "DENY", "reason": "ACTION_OUTSIDE_TASK_SCOPE"}

        # 4. Default ALLOW if all checks pass
        decision_record = create_audit_record(context, payload, "ALLOW", "TASK_SCOPE_MATCH", "Action matches task scope and intent", start_time)
        AUDIT_LOGS.append(decision_record)

    except Exception as e:
        # FAIL-CLOSED: Any unexpected error forces a DENY
        return {"decision": "DENY", "reason": f"INTERNAL_ERROR_FAIL_CLOSED: {str(e)}"}

    # 5. Execute the allowed action on the agent's behalf
    return {"decision": "ALLOW", "reason": "TASK_SCOPE_MATCH", "execution": execute_action(payload)}

def execute_action(payload: ToolRequestPayload) -> Optional[Dict[str, Any]]:
    """Forwards an allowed action to the downstream API using the scanner-held credential."""
    if payload.tool != "booking" or payload.operation != "cancel":
        return None
    try:
        res = httpx.delete(
            f"{BOOKING_API_URL}/reservations/{payload.resource_id}",
            headers={"X-API-Key": BOOKING_API_KEY},
            timeout=5.0,
        )
        return {"status_code": res.status_code, "response": res.json()}
    except Exception as e:
        return {"error": str(e)}

def create_audit_record(context, payload, decision, rule, reason, start_time):
    latency_ms = int((time.time() - start_time) * 1000)
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_id": context.get("task_id", "unknown"),
        "agent_id": context.get("agent_id", "booking-agent"),
        "subject": {
            "user_id": context.get("user_id"),
            "tenant_id": context.get("tenant_id", "demo")
        },
        "tool": payload.tool,
        "operation": payload.operation,
        "resource_id": payload.resource_id,
        "decision": decision,
        "rule": rule,
        "reason": reason,
        "latency_ms": latency_ms
    }

@app.get("/audit/logs")
def get_audit_logs():
    return AUDIT_LOGS