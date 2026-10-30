import hmac
import hashlib
import json
import os
import requests
import time

API_URL = "http://127.0.0.1:8001"
SCANNER_URL = "http://127.0.0.1:8002"
# Host application's signing secret (must match the scanner's SCANNER_SIGNING_SECRET)
SECRET_KEY = os.environ.get("SCANNER_SIGNING_SECRET", "dev-only-signing-secret").encode("utf-8")
# Booking API credential the agent held in the unprotected baseline (Test 1 only)
BASELINE_AGENT_API_KEY = os.environ.get("BOOKING_API_KEY", "dev-only-booking-key")

def sign_context(context: dict) -> str:
    canonical_data = json.dumps(context, sort_keys=True).encode("utf-8")
    return hmac.new(SECRET_KEY, canonical_data, hashlib.sha256).hexdigest()

def run_yc_pitch_demo():
    print("==================================================")
    print("   YCAgentScanner — Flagship Gym-Booking Demo     ")
    print("   Executing Five Live Enforcement Tests          ")
    print("==================================================\n")

    # Reset mock API state
    requests.post(f"{API_URL}/reset")

    # --------------------------------------------------
    # TEST 1: Vulnerable baseline
    # --------------------------------------------------
    print("--- [Test 1] Vulnerable Baseline ---")
    print("Agent attempts direct cancellation of another user's reservation (R001)...")
    
    res = requests.delete(f"{API_URL}/reservations/R001", headers={"X-API-Key": BASELINE_AGENT_API_KEY})
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
    print("Narration: 'The agent has valid booking API access. While performing a class-booking task, it discovers and calls a cancellation endpoint for reservation R001. The downstream API accepts the action. Valid credentials do not guarantee that each agent action belongs to the user’s current task.'\n")
    
    # Reset API state for subsequent tests
    requests.post(f"{API_URL}/reset")
    time.sleep(1)

    # --------------------------------------------------
    # TEST 2: Runtime enforcement
    # --------------------------------------------------
    print("--- [Test 2] Runtime Enforcement ---")
    task_context_t1 = {
        "task_id": "T-123",
        "agent_id": "booking-agent",
        "user_id": "U123",
        "tenant_id": "demo",
        "intent": "book_class",
        "allowed_tools": ["booking", "search"],
        "resource_scope": {"reservation_ids": ["R123"]}
    }
    sig_t1 = sign_context(task_context_t1)

    payload = {
        "task_context": task_context_t1,
        "signature": sig_t1,
        "tool": "booking",
        "operation": "cancel",
        "resource_id": "R001"
    }

    print("Agent proposes: cancel_reservation(R001) routed through YCAgentScanner...")
    eval_res = requests.post(f"{SCANNER_URL}/evaluate", json=payload)
    eval_data = eval_res.json()
    print(f"Scanner Verdict: {eval_data}")
    
    metrics = requests.get(f"{API_URL}/metrics").json()
    print(f"Booking API cancellation requests received: {metrics['cancellation_requests_received']}")
    print("Narration: 'The same agent proposes the same cancellation. This time it routes through the scanner. The scanner verifies the trusted task context and denies the cancellation before the booking API is called.'\n")

    # --------------------------------------------------
    # TEST 3: Task binding (The core differentiation)
    # --------------------------------------------------
    print("--- [Test 3] Task Binding ---")
    # Part A: book_class task -> DENY
    print("Part A: Same reservation (R123), Task: book_class -> Expected DENY")
    task_context_a = {
        "task_id": "T-124",
        "agent_id": "booking-agent",
        "user_id": "U123",
        "intent": "book_class",
        "allowed_tools": ["booking"],
        "resource_scope": {"reservation_ids": ["R123"]}
    }
    payload_a = {
        "task_context": task_context_a,
        "signature": sign_context(task_context_a),
        "tool": "booking",
        "operation": "cancel",
        "resource_id": "R123"
    }
    print(f"Result: {requests.post(f'{SCANNER_URL}/evaluate', json=payload_a).json()}")

    # Part B: cancel_my_reservation task -> ALLOW
    print("Part B: Same reservation (R123), Task: cancel_my_reservation -> Expected ALLOW")
    task_context_b = {
        "task_id": "T-125",
        "agent_id": "booking-agent",
        "user_id": "U123",
        "intent": "cancel_my_reservation",
        "allowed_tools": ["booking"],
        "resource_scope": {"reservation_ids": ["R123"]}
    }
    payload_b = {
        "task_context": task_context_b,
        "signature": sign_context(task_context_b),
        "tool": "booking",
        "operation": "cancel",
        "resource_id": "R123"
    }
    print(f"Result: {requests.post(f'{SCANNER_URL}/evaluate', json=payload_b).json()}")
    print("Narration: 'Nothing about the identity, agent, API, resource, or operation changed. Only the trusted task changed. Under a class-booking task, cancellation is denied. Under a reservation-cancellation task, the exact same action is allowed, and the scanner executes it against the booking API using its own credential.'\n")

    # --------------------------------------------------
    # TEST 4: Forged context
    # --------------------------------------------------
    print("--- [Test 4] Forged Context ---")
    print("Agent attempts to modify the signed task context (changing user/scope)...")
    forged_context = task_context_t1.copy()
    forged_context["user_id"] = "U999_HACKER"

    forged_payload = {
        "task_context": forged_context,
        "signature": sig_t1, # Original signature won't match forged content
        "tool": "booking",
        "operation": "cancel",
        "resource_id": "R123"
    }
    print(f"Scanner Verdict: {requests.post(f'{SCANNER_URL}/evaluate', json=forged_payload).json()}")
    print("Narration: 'The agent can propose an operation, but it cannot expand its authority by changing the user, task, or resource scope. Signature verification fails and no protected operation is executed.'\n")

    # --------------------------------------------------
    # TEST 5: Direct bypass simulation
    # --------------------------------------------------
    print("--- [Test 5] Direct Bypass ---")
    print("Agent attempts a direct call to the Booking API, bypassing the scanner (no API key in its runtime)...")
    res = requests.delete(f"{API_URL}/reservations/R001")
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.json()}")
    print("Narration: 'In the protected deployment, the Booking API credential lives only in the scanner. The agent can still reach the API, but without the credential the direct call is rejected. Network isolation would add a second layer; this demo does not simulate it.'\n")

    # --------------------------------------------------
    # Audit Timeline Output
    # --------------------------------------------------
    print("==================================================")
    print("                AUDIT TIMELINE                    ")
    print("==================================================")
    logs = requests.get(f"{SCANNER_URL}/audit/logs").json()
    
    print(f"{'TIMESTAMP':<20} {'TASK_ID':<10} {'ACTION':<15} {'DECISION':<10} {'REASON'}")
    print("-" * 75)
    for log in logs:
        action_str = f"{log['tool']}.{log['operation']}({log['resource_id']})"
        print(f"{log['timestamp']:<20} {log['task_id']:<10} {action_str:<15} {log['decision']:<10} {log['reason']}")

    print("\nSample Audit JSON Record:")
    if logs:
        print(json.dumps(logs[0], indent=2))
    print("==================================================")

if __name__ == "__main__":
    run_yc_pitch_demo()