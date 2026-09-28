import urllib.request
import json

URL = "http://127.0.0.1:8000/api/agent/tool-call"

test_cases = [
    {
        "name": "TEST 1: Legitimate Request (Expected: 200 OK)",
        "payload": {
            "token_claims": {
                "sub": "alice",
                "tenant": "Acme",
                "act": { "client_id": "support-agent-17", "role": "support-agent" }
            },
            "tool_call": {
                "tool": "customer_lookup",
                "tenant_context": "Acme",
                "rows_requested": 10,
                "purpose": "support_ticket_4812"
            }
        }
    },
    {
        "name": "TEST 2: Bulk Export / Prompt Injection Block (Expected: 403 Forbidden)",
        "payload": {
            "token_claims": {
                "sub": "alice",
                "tenant": "Acme",
                "act": { "client_id": "support-agent-17", "role": "support-agent" }
            },
            "tool_call": {
                "tool": "customer_lookup",
                "tenant_context": "Acme",
                "rows_requested": 1000000,
                "purpose": "injected_malicious_export"
            }
        }
    },
    {
        "name": "TEST 3: Tenant Boundary Mismatch (Expected: 400 Bad Request)",
        "payload": {
            "token_claims": {
                "sub": "alice",
                "tenant": "Acme",
                "act": { "client_id": "support-agent-17", "role": "support-agent" }
            },
            "tool_call": {
                "tool": "get_record",
                "tenant_context": "Globex",
                "record_id": 103,
                "purpose": "cross_tenant_probe"
            }
        }
    }
]

print("==================================================")
print("RUNNING YCAGENTSCANNER AUTOMATED TEST SUITE")
print("==================================================")

for i, test in enumerate(test_cases, 1):
    print(f"\n[{i}] {test['name']}")
    req = urllib.request.Request(
        URL,
        data=json.dumps(test["payload"]).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            body = json.loads(response.read().decode("utf-8"))
            print(f"Status Code: {status_code} ✅")
            print(f"Response: {json.dumps(body, indent=2)}")
    except urllib.error.HTTPError as e:
        status_code = e.code
        body = json.loads(e.read().decode("utf-8"))
        print(f"Status Code: {status_code} 🛡️ (Blocked/Handled)")
        print(f"Response: {json.dumps(body, indent=2)}")
    except Exception as ex:
        print(f"Error: {ex}")

print("\n==================================================")
print("TEST SUITE COMPLETED")
print("==================================================")