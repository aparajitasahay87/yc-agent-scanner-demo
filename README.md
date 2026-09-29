# YCAgentScanner

> **Identity tells you who the agent is. Runtime authorization determines what that agent is allowed to do right now.**

YCAgentScanner is a lightweight, self-hosted **runtime authorization layer for AI agents**.

It sits between an AI agent and the tools it wants to use—APIs, databases, internal services, and other application capabilities—and evaluates each requested action against **trusted application context and explicit authorization policies** before execution.

The goal is simple:

**A valid agent identity should not automatically make every dynamically generated action valid.**

---

## 🎯 The Problem

AI agents are increasingly able to autonomously call:

- Databases
- APIs
- Internal tools
- Customer systems
- Administrative functions

Traditional identity and access-control systems are designed primarily around questions such as:

> **Who is this agent?**

and:

> **What resources can this identity access?**

But autonomous agents introduce another question:

> **Is this specific action authorized in the context of what the application asked the agent to do?**

An agent may have:

- A valid identity
- A valid token
- Access to the requested resource
- A valid session

…and still attempt an action that violates:

- Task boundaries
- Tenant isolation
- Data-volume limits
- Tool-level permissions
- Application-defined intent

This creates a gap between **identity authorization** and **runtime action authorization**.

---

## 💡 The Solution

**YCAgentScanner** acts as a **Policy Enforcement Point (PEP)** between an AI agent and its tools.

Before a tool call executes, YCAgentScanner evaluates the request using trusted context such as:

- Agent identity
- Tenant
- Application-defined task context
- Requested tool/action
- Resource
- Explicit policy
- Runtime constraints

It produces a deterministic, auditable decision:

```text
ALLOW
```

or:

```text
DENY
```

The scanner does not give the LLM authority to define its own permissions.

Instead, the **trusted host application establishes the authorization context**, and the scanner evaluates whether the agent's requested action is consistent with that context.

---

## 🏗️ Core Architecture

### Intent Does NOT Come From the LLM

This is a fundamental design principle of YCAgentScanner.

The LLM should not be able to redefine its own authorization context by simply generating a different intent.

Instead:

```text
┌─────────────────────────────┐
│      Trusted Application    │
│                             │
│ Establishes task context    │
│ intent = resolve_support    │
│ ticket                      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│          AI Agent           │
│                             │
│ Requests a tool/action      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      YCAgentScanner / PEP   │
│                             │
│ Identity                    │
│ Tenant                      │
│ Trusted Context             │
│ Requested Action            │
│ Policy                      │
└──────────────┬──────────────┘
               │
          ┌────┴────┐
          ▼         ▼
       ALLOW       DENY
          │         │
          ▼         ▼
      Execute     Block
       Action      Action
```

### Why This Matters

The agent controls **what it requests**.

The trusted application controls **what task context it is authorized to operate within**.

YCAgentScanner determines whether the requested action is permitted.

---

## 🧪 MVP Demo

The MVP demonstrates four authorization scenarios.

### 1. Normal Authorized Access — `ALLOW`

The agent requests an action that is consistent with:

- Its identity
- Tenant
- Role
- Task context
- Policy

**Result:**

```text
ALLOW
```

---

### 2. Excessive / Bulk Access — `DENY`

The agent attempts to retrieve more records than its policy allows.

Example:

```text
Policy limit: 100 records
Agent request: 10,000 records
```

**Result:**

```text
DENY
```

This demonstrates runtime enforcement of data-volume constraints.

---

### 3. Cross-Tenant Access — `DENY`

The agent attempts to access a resource belonging to a different tenant.

Example:

```text
Agent tenant: acme
Requested resource tenant: globex
```

**Result:**

```text
DENY
```

The authorization decision is made at runtime before the tool executes.

---

### 4. Context Drift — `DENY`

This is the core YCAgentScanner demonstration.

The agent receives a legitimate task:

```text
intent = resolve_support_ticket
```

The agent initially performs an authorized lookup:

```text
customer_lookup
```

Later, because of prompt injection, model behavior, or other runtime conditions, it attempts:

```text
export_all_customers
```

The agent may still have:

- A valid identity
- A valid token
- A valid session
- Access to the underlying system

But the requested action conflicts with the trusted application context.

**Result:**

```text
DENY
```

---

## 🎬 Main Demo: Valid Identity, Wrong Action

The primary demo follows this flow.

### Step 1 — Establish Trusted Context

The host application establishes the task outside of the LLM:

```json
{
  "intent": "resolve_support_ticket"
}
```

### Step 2 — Legitimate Tool Call

The agent requests:

```text
customer_lookup
```

The scanner evaluates the request and returns:

```text
ALLOW
```

### Step 3 — Agent Goes Off-Task

The agent subsequently requests:

```text
export_all_customers
```

The trusted context still indicates:

```text
resolve_support_ticket
```

### Step 4 — Runtime Authorization Decision

YCAgentScanner detects the mismatch:

```text
INTENT_ACTION_MISMATCH
```

and blocks the request.

Example decision:

```json
{
  "decision": "DENY",
  "policy": "SUPPORT_CUSTOMER_ACCESS",
  "reason": "INTENT_ACTION_MISMATCH",
  "agent_id": "support-agent-17",
  "tenant_id": "acme",
  "tool": "export_all_customers"
}
```

The decision is both **machine-readable and auditable**.

---

## 🔐 Authorization Model

At a high level:

```text
Authorization Decision
        =
Identity
+ Tenant
+ Trusted Task Context
+ Requested Action
+ Resource
+ Policy
+ Runtime Constraints
```

The scanner evaluates these inputs before allowing the action to reach the underlying tool.

Conceptually:

```text
if action_is_authorized(context, request, policy):
    ALLOW
else:
    DENY
```

The important distinction is that **authorization is evaluated at action time**, rather than relying solely on permissions established when the agent's credentials were issued.

---

## 🧱 Architecture Components

| Component | Responsibility |
|---|---|
| Trusted Application | Establishes task context and authorization intent |
| AI Agent | Generates tool/action requests |
| YCAgentScanner | Evaluates runtime authorization |
| Policy Engine | Defines authorization rules |
| Tool / API / Database | Executes only authorized requests |
| Audit Decision | Records `ALLOW` / `DENY` and decision context |

---

## 🔐 Example Authorization Flow

```text
1. Application creates trusted task context
                │
                ▼
2. Agent receives task
                │
                ▼
3. Agent generates tool request
                │
                ▼
4. YCAgentScanner intercepts request
                │
                ▼
5. Scanner evaluates:
   - Identity
   - Tenant
   - Intent
   - Tool
   - Resource
   - Policy
   - Runtime constraints
                │
          ┌─────┴─────┐
          ▼           ▼
       ALLOW         DENY
          │           │
          ▼           ▼
    Tool executes   Request blocked
```

---

## 🚀 Quick Start

### 1. Clone the Repository

```powershell
git clone https://github.com/your-username/yc-agent-scanner-demo.git
cd yc-agent-scanner-demo
```

### 2. Create a Virtual Environment

```powershell
python -m venv venv
```

### 3. Activate the Virtual Environment

#### Windows PowerShell

```powershell
.\venv\Scripts\Activate
```

#### macOS / Linux

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Run the API

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The API will be available locally at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 🧪 Run the Test Suite

Open a second terminal, activate the virtual environment, and run:

```bash
python run_tests.py
```

The test suite demonstrates the authorization scenarios implemented by the MVP.

---

## 📁 Project Structure

```text
YCAgentScanner/
│
├── app/
│   ├── main.py
│   └── ...
│
├── tests/
│   └── ...
│
├── run_tests.py
├── requirements.txt
├── README.md
└── ...
```

---

## 🛡️ What YCAgentScanner Is

YCAgentScanner is:

- A runtime authorization layer
- A Policy Enforcement Point
- Self-hosted
- Lightweight
- Designed for AI-agent tool calls
- Deterministic at the authorization boundary
- Auditable through explicit policy decisions

---

## 🚫 What YCAgentScanner Is Not

YCAgentScanner is not:

- An identity provider
- A replacement for authentication
- A replacement for IAM
- An LLM safety model
- A prompt-injection detector
- An LLM that decides whether another LLM is trustworthy

Instead, it operates **after the agent generates an action but before that action reaches the protected tool**.

---

## 🧠 Core Insight

Traditional authorization often answers:

> **Can this identity access this resource?**

YCAgentScanner adds another runtime question:

> **Is this specific action authorized in the trusted context in which this agent is operating?**

This distinction becomes increasingly important as software moves from deterministic applications toward autonomous agents.

---

## 🗣️ 60-Second YC Pitch

> AI agents can now autonomously call databases, APIs, and internal tools. Traditional identity systems can establish who an agent is and what resources it can access, but a valid identity doesn't necessarily authorize every dynamically generated action the agent takes.
>
> We built **YCAgentScanner**, a lightweight, self-hosted runtime authorization layer that sits between an agent and its tools. Before a tool call executes, it evaluates the agent's trusted application context against the actual requested action and returns a deterministic, auditable policy decision.
>
> The key insight is simple:
>
> **Identity tells you who the agent is; runtime authorization determines what that agent is allowed to do right now.**
>
> Our MVP demonstrates this with a support-agent scenario: the agent is legitimately authorized to resolve a customer ticket, but when it attempts to export all customers, YCAgentScanner blocks the action—even though the agent's identity and credentials remain valid.

---

## 🔭 Future Direction

Potential areas for future development include:

- Policy-as-code
- Framework integrations for agent runtimes
- FastAPI middleware
- LangGraph integration
- Tool-level authorization
- Resource-level authorization
- Rate and volume controls
- Multi-tenant policy enforcement
- Richer audit trails
- Policy management APIs
- Distributed deployment
- Integration with existing identity and IAM systems

---

## ⚠️ Current Status

**YCAgentScanner is an MVP / proof of concept.**

The current implementation is intended to demonstrate the runtime authorization model and core policy-enforcement flows.

It should not be considered a production security boundary without additional security review, testing, hardening, and operational controls.

---

## Support Agent Demo — Architecture Flow

```text
┌──────────────────────────────────┐
│        Support Agent Demo        │
│                                  │
│ Ticket: #123                     │
│ Customer: 1042                   │
│                                  │
│ "Resolve this customer's issue"  │
│                                  │
│          [Run Agent]             │
└──────────────────┬───────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  Host FastAPI   │
         │      App        │
         └────────┬────────┘
                  │
          establishes context
                  │
                  ▼
         ┌─────────────────┐
         │     AI Agent    │
         └────────┬────────┘
                  │
             tool request
                  │
                  ▼
         ┌─────────────────┐
         │ YCAgentScanner  │
         │                 │
         │   ALLOW / DENY  │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Mock Database  │
         └─────────────────┘
```

### Request Flow

1. The user submits a support request through the **Support Agent Demo**.
2. The **Host FastAPI App** establishes the runtime context.
3. The **AI Agent** receives the request and generates a tool request.
4. **YCAgentScanner** intercepts the tool request before it reaches the database.
5. YCAgentScanner evaluates the request against the runtime context and authorization rules.
6. The request is either **ALLOWED** or **DENIED**.
7. Only an allowed request reaches the **Mock Database**.


## 📜 License

Add your license here.
