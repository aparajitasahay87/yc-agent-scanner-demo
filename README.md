# YCAgentScanner 🛡️
### Deterministic Runtime Policy Enforcement for Autonomous AI Agents

> **The Host Application** establishes the trusted task context.  
> **The Agent** decides what to do next.  
> **YCAgentScanner** enforces the authorization boundary at runtime.

> **Identity tells you who the agent is. Runtime authorization determines what that agent is allowed to do right now.**

YCAgentScanner is a lightweight, self-hosted **runtime authorization layer for AI agents**.

It sits between an AI agent and the tools it wants to use (APIs, databases, internal services) and evaluates each requested action against **trusted, host-signed task context** before execution.

The goal is simple:

**A valid agent identity should not automatically make every dynamically generated action valid.**

---

## 🎯 The Problem

AI agents increasingly call APIs, databases, and internal tools on their own. Traditional identity and access control answers:

> **Who is this agent?** and **What resources can this identity access?**

Autonomous agents introduce another question:

> **Is this specific action authorized in the context of what the application asked the agent to do?**

An agent may have a valid identity, a valid token, and access to the requested resource, and still attempt an action that has nothing to do with its current task: through prompt injection, a model mistake, or a tool it "discovered" along the way.

This is the gap between **identity authorization** and **runtime action authorization**.

---

## 🤔 Why a Separate Runtime Scanner?

A common question is: *"Why not just put these checks directly inside the host application?"*

Traditional backend workflows are largely deterministic: the application explicitly defines which API or database operation should execute next.

Autonomous AI agents, however, can dynamically select tools and determine the sequence of actions needed to complete a task. The exact action taken at runtime may not be known when the host initially creates the task.

This creates a distinct enforcement point:

> **The host establishes the task context. The agent proposes the action. The runtime enforcement layer decides whether that action is authorized before the protected resource is accessed.**

---

## 💡 The Approach

YCAgentScanner acts as a **Policy Enforcement Point (PEP)** between the agent and its tools.

1. **The trusted host application defines the task**, not the LLM. It builds a task context (user, intent, allowed tools, resource scope) and signs it with HMAC-SHA256.
2. **The agent proposes an action** (tool, operation, resource) and sends it to the scanner together with the signed context.
3. **The scanner verifies the signature**, then checks the action against the context.
4. **On ALLOW, the scanner executes the action** using a downstream credential that only the scanner holds. On DENY, the call never reaches the API.
5. **Every decision is written to an audit log.**
6. **It fails closed:** any unexpected error during evaluation results in DENY.

```text
┌──────────────────────────┐
│   Trusted Application    │  builds + signs task context
│   intent = book_class    │  (user, allowed tools, resource scope)
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│        AI Agent          │  proposes: booking.cancel(R001)
│  (holds no API creds)    │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│   YCAgentScanner (PEP)   │  1. verify signature
│                          │  2. tool allowed for task?
│  holds Booking API key   │  3. resource in task scope?
│                          │  4. operation fits intent?
└──────┬────────────┬──────┘
       ▼            ▼
     ALLOW         DENY ──► audit log
       │
       ▼
┌──────────────────────────┐
│       Booking API        │
└──────────────────────────┘
```

The agent controls **what it requests**. The trusted application controls **what task it is operating within**. The scanner decides whether the two are consistent.

---

## 🎬 Demo: Gym Booking Agent

The demo uses a booking agent for a gym. The downstream Booking API is **intentionally vulnerable**: it requires an API key but performs no ownership check, so any caller with the key can cancel anyone's reservation. This mirrors a common real-world situation, where the agent's tool credential is broader than any single task.

| Reservation | Owner |
|---|---|
| `R123` | `U123` (the user the agent is acting for) |
| `R001` | `U456` (someone else) |

`run_yc_pitch_demo.py` runs five live tests against the running services:

| # | Test | What happens | Result |
|---|---|---|---|
| 1 | **Vulnerable baseline** | Agent holds the API key and calls `DELETE /reservations/R001` directly | `200`: another user's reservation is cancelled |
| 2 | **Runtime enforcement** | Same cancellation, routed through the scanner under a `book_class` task scoped to `R123` | `DENY ACTION_OUTSIDE_TASK_SCOPE`; Booking API receives 0 requests |
| 3 | **Task binding** | Cancel `R123` (the user's own reservation) under two different tasks | `book_class` → `DENY`; `cancel_my_reservation` → `ALLOW`, executed by the scanner |
| 4 | **Forged context** | Agent edits `user_id` in the signed context and reuses the old signature | `DENY INVALID_SIGNATURE` |
| 5 | **Direct bypass** | Agent (with no API key in its runtime) calls the Booking API directly | `401`: rejected by the API |

**Test 3 is the core idea.** Identity, agent, API, resource and operation are all identical. Only the trusted task changes, and the decision flips.

Example audit record:

```json
{
  "timestamp": "2026-10-30T17:10:09Z",
  "task_id": "T-123",
  "agent_id": "booking-agent",
  "subject": { "user_id": "U123", "tenant_id": "demo" },
  "tool": "booking",
  "operation": "cancel",
  "resource_id": "R001",
  "decision": "DENY",
  "rule": "ACTION_OUTSIDE_TASK_SCOPE",
  "reason": "Resource R001 is outside task scope",
  "latency_ms": 0
}
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/aparajitasahay87/yc-agent-scanner-demo.git
cd yc-agent-scanner-demo
python -m venv venv
# Windows: .\venv\Scripts\Activate    macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Secrets are read from environment variables. If they are unset, insecure `dev-only-*` defaults are used so the demo runs out of the box. Set real values for anything beyond a local demo.

| Variable | Used by | Purpose |
|---|---|---|
| `SCANNER_SIGNING_SECRET` | scanner, demo script (as host app) | HMAC key for signing task context |
| `BOOKING_API_KEY` | mock API, scanner | Credential for mutating Booking API calls |
| `BOOKING_API_URL` | scanner | Booking API base URL (default `http://127.0.0.1:8001`) |

### Run the demo

Use three terminals, each with the virtual environment activated:

```bash
# Terminal 1: vulnerable Booking API
uvicorn mock_api.main:app --port 8001

# Terminal 2: YCAgentScanner
uvicorn scanner.main:app --port 8002

# Terminal 3: run the five tests
python run_yc_pitch_demo.py
```

The scanner's audit log is also available at `http://127.0.0.1:8002/audit/logs`, and interactive API docs at `/docs` on either service.

---

## 📁 Project Structure

```text
yc-agent-scanner-demo/
├── scanner/main.py          # YCAgentScanner PEP: signature check, policy, execution, audit
├── mock_api/main.py         # Intentionally vulnerable Booking API
├── run_yc_pitch_demo.py     # Five-test demo (also plays the trusted host application)
├── app/                     # Earlier prototype (support-agent scenario, unsigned context)
├── run_tests.py             # Tests for the earlier prototype in app/
└── requirements.txt
```

`app/` contains the first iteration of the idea: a support agent blocked from `export_all_customers` during a `resolve_support_ticket` task, plus tenant and bulk-access checks. It is kept for reference. The gym-booking demo above is the current design: it adds signed context, scanner-held credentials, and execution through the PEP.

---

## 🛡️ What YCAgentScanner Is (and Isn't)

**It is** a runtime authorization layer and Policy Enforcement Point for agent tool calls. It is self-hosted, deterministic at the decision boundary, and auditable.

**It is not** an identity provider, a replacement for IAM or authentication, a prompt-injection detector, or an LLM judging another LLM. It operates **after the agent proposes an action and before that action reaches the protected tool.**

---

## ⚠️ Current Status and Limitations

**This is a proof of concept, not a production security boundary.** Known limitations:

- **No real LLM in the loop.** The demo sends hand-written tool calls to show the enforcement path deterministically. Wiring in an agent framework is future work.
- **Policies are hard-coded** in `scanner/main.py` rather than expressed as policy-as-code (e.g. OPA/Rego or Cedar).
- **Bypass protection relies on credential placement only.** Test 5 shows the agent cannot call the API without the key. It does not simulate network isolation, which a real deployment should add.
- **Signed contexts do not expire.** There is no timestamp, nonce, or replay protection yet.
- **A shared HMAC secret** is used instead of asymmetric signatures or a token format such as JWT.
- **The audit log is in memory** and resets when the scanner restarts.
- **The scanner does not replace server-side checks.** The Booking API should still verify ownership; the scanner adds task-level authorization on top.

---

## 🔭 Future Direction

- Real agent integration (e.g. LangGraph or MCP tool-call interception)
- Declarative policy-as-code
- Context expiry, nonces and replay protection
- Asymmetric signing / integration with existing IAM token exchange
- Persistent, tamper-evident audit trail
- Network-level isolation in the reference deployment

---

## 📜 License

Add your license here.
