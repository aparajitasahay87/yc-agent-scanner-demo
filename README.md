# YCAgentScanner

> **Identity tells you who the agent is. Runtime authorization determines what that agent is allowed to do right now.**

YCAgentScanner moves authorization from the moment a credential is issued to the moment an AI agent actually takes an action.

---

## 🎯 The Problem

AI agents can autonomously call databases, APIs, and internal tools. Traditional identity systems can establish who an agent is and what broad resources it can access, but **a valid credential does not necessarily authorize every dynamically generated action against that resource.**

An agent can have a completely valid token and still attempt to violate tenant boundaries, data-volume limits, or task scopes.

---

## 💡 The Solution

**YCAgentScanner** is a lightweight, self-hosted runtime authorization layer (Policy Enforcement Point) that sits between an agent and its tools. 

Before any tool call executes, it evaluates the agent's identity, tenant, application task context, and explicit policy to return an **auditable policy decision (`ALLOW` / `DENY`).**

---

## 🏗️ The Critical Architecture: Intent Does NOT Come From the LLM

To prevent an LLM from redefining its own permissions on the fly, intent is established outside the model by the trusted host application:

```text
Trusted Application
     ↓ (Establishes task context: intent = resolve_support_ticket)
AI Agent
     ↓ (Requests tool call)
YCAgentScanner / PEP
     ↓ (Evaluates requested action against trusted context)
ALLOW / DENY

```markdown
---

## 🧪 The MVP Demo — Four Scenarios

* **Normal Authorized Access (`ALLOW`):** Standard tool invocation within role and scope bounds[cite: 2].
* **Excessive / Bulk Access (`DENY`):** Enforces hard volume/record limits per role to handle bulk-access policy violations[cite: 2].
* **Cross-Tenant Isolation (`DENY`):** Enforces strict resource and tenant boundaries[cite: 2].
* **Context Drift (`DENY` - The Core Demo):** Intercepts agents whose valid session attempts to execute tools that contradict their application-bound task intent[cite: 2].

---

## 🎬 The Main YC Demo: Valid Identity, Wrong Action

* **Step 1 — Establish Trusted Context:** The host application defines the task (`intent = resolve_support_ticket`) outside LLM control[cite: 2].
* **Step 2 — Legitimate Action:** The agent requests a permitted tool (`customer_lookup`), and the scanner returns **`ALLOW`**[cite: 2].
* **Step 3 — Agent Goes Off-Task:** Prompt injection or model drift causes the agent to request an unauthorized tool (`export_all_customers`)[cite: 2].
* **Result:** The identity and token are completely valid, but the action does not match the authorized task. Outcome: **`DENY`** + an auditable policy decision[cite: 2].

```json
{
  "decision": "DENY",
  "policy": "SUPPORT_CUSTOMER_ACCESS",
  "reason": "INTENT_ACTION_MISMATCH",
  "agent_id": "support-agent-17",
  "tenant_id": "acme",
  "tool": "export_all_customers"
}

---

## 🚀 Quick Start & Local Setup

### 1. Clone & Setup Environment
```powershell
git clone [https://github.com/your-username/yc-agent-scanner-demo.git](https://github.com/your-username/yc-agent-scanner-demo.git)
cd yc-agent-scanner-demo
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt

# YCAgentScanner

A lightweight, self-hosted runtime authorization layer that sits between an autonomous AI agent and its tools.

## 🗣️ The 60-Second YC Pitch

> "AI agents can now autonomously call databases, APIs, and internal tools. Traditional identity systems can establish who an agent is and what resources it can access, but a valid identity doesn't necessarily authorize every dynamically generated action the agent takes."

> "We built **YCAgentScanner**, a lightweight, self-hosted runtime authorization layer that sits between an agent and its tools. Before a tool call executes, it evaluates the agent's trusted application context against the actual requested action and returns a deterministic, auditable policy decision."

> "The key insight is simple: **identity tells you who the agent is; runtime authorization determines what that agent is allowed to do right now.**"

---

## 🚀 Getting Started

### 1. Run the FastAPI Server

Open your terminal and run:

```powershell
uvicorn app.main:app --reload

### 2. Run the Test Suite

Open a second terminal window, activate your virtual environment, and run:

```powershell
python run_tests.py
```

## 🗣️ The 60-Second YC Pitch

> "AI agents can now autonomously call databases, APIs, and internal tools. Traditional identity systems can establish who an agent is and what resources it can access, but a valid identity doesn't necessarily authorize every dynamically generated action the agent takes."

> "We built **YCAgentScanner**, a lightweight, self-hosted runtime authorization layer that sits between an agent and its tools. Before a tool call executes, it evaluates the agent's trusted application context against the actual requested action and returns a deterministic, auditable policy decision."

> "The key insight is simple: **identity tells you who the agent is; runtime authorization determines what that agent is allowed to do right now.**"