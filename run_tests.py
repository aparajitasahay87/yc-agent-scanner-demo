import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1/enforce"

tests = [
    {
        "name": "Test 1: Policy 1 — Normal Access (Should ALLOW)",
        "payload": {
            "context": {
                "agent_id": "support-agent-17",
                "user_id": "user-892",
                "tenant_id": "acme",
                "current_tenant": "acme",
                "intent": "resolve_support_ticket"
            },
            "action": {
                "tool_name": "customer_lookup",
                "record_count": 1,
                "record_id": 101
            }
        }
    },
    {
        "name": "Test 2: Policy 2 — Excessive / Bulk Access (Should DENY)",
        "payload": {
            "context": {
                "agent_id": "support-agent-17",
                "user_id": "user-892",
                "tenant_id": "acme",
                "current_tenant": "acme",
                "intent": "resolve_support_ticket"
            },
            "action": {
                "tool_name": "customer_lookup",
                "record_count": 5000,
                "record_id": 101
            }
        }
    },
    {
        "name": "Test 3: Policy 3 — Cross-Tenant Access (Should DENY)",
        "payload": {
            "context": {
                "agent_id": "support-agent-17",
                "user_id": "user-892",
                "tenant_id": "acme",
                "current_tenant": "globex",
                "intent": "resolve_support_ticket"
            },
            "action": {
                "tool_name": "customer_lookup",
                "record_count": 1,
                "record_id": 103
            }
        }
    },
    {
        "name": "Test 4: Context Drift / Wrong Intent (Should DENY)",
        "payload": {
            "context": {
                "agent_id": "support-agent-17",
                "user_id": "user-892",
                "tenant_id": "acme",
                "current_tenant": "acme",
                "intent": "resolve_support_ticket"
            },
            "action": {
                "tool_name": "export_all_customers",
                "record_count": 1,
                "record_id": 101
            }
        }
    }
]

def run_tests():
    print("🚀 Running Agent PEP Policy Test Suite...\n")
    for test in tests:
        print(f"--- {test['name']} ---")
        try:
            response = httpx.post(BASE_URL, json=test["payload"])
            print(f"HTTP Status Code: {response.status_code}")
            print("Response Body:")
            print(response.json())
        except httpx.ConnectError:
            print("❌ Error: Could not connect to FastAPI server. Make sure 'uvicorn app.main:app --reload' is running!")
            break
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    run_tests()