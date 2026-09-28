#!/bin/bash

BASE_URL="http://127.0.0.1:8000/api/agent/tool-call"

echo "=== TEST 1: Legitimate Request (200 OK) ==="
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{
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
  }' | json_pp 2>/dev/null || curl -s -X POST $BASE_URL -H "Content-Type: application/json" -d '{"token_claims": {"sub": "alice", "tenant": "Acme", "act": {"client_id": "support-agent-17", "role": "support-agent"}}, "tool_call": {"tool": "customer_lookup", "tenant_context": "Acme", "rows_requested": 10, "purpose": "support_ticket_4812"}}'
echo -e "\n--------------------------------------------------\n"

echo "=== TEST 2: Bulk Export / Prompt Injection Block (403 Forbidden) ==="
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
echo -e "\n--------------------------------------------------\n"

echo "=== TEST 3: Tenant Boundary Mismatch (400 Bad Request) ==="
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
echo -e "\n"