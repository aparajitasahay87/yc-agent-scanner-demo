# main.py
from fastapi import FastAPI, Request
import uvicorn
from yc_agent_scanner import YCAgentScanner, SecurityRule
from database import DATABASE_STORE

app = FastAPI(title="Developer API with YCAgentScanner SDK")

# 1. Initialize SDK rules (e.g., support agent limits)
scanner = YCAgentScanner(
    policies=[
        SecurityRule(
            role="support-agent",
            allowed_tools=["customer_lookup", "get_record"],
            max_rows=50,
            enforce_tenant_match=True
        )
    ]
)

# 2. Mount the SDK middleware
app.middleware("http")(scanner.fastapi_middleware())

# 3. Downstream database-connected tool endpoint
@app.post("/api/agent/tool-call")
async def execute_tool(request: Request):
    body = await request.json()
    tool_call = body.get("tool_call", {})
    record_id = tool_call.get("record_id")
    
    # If the tool call requests a specific record ID, fetch it from the database store
    if record_id:
        record = DATABASE_STORE.get(record_id)
        return {
            "status": "SUCCESS", 
            "code": 200,
            "executed_tool": tool_call.get("tool"),
            "retrieved_data": record
        }
        
    return {
        "status": "SUCCESS", 
        "code": 200,
        "executed_tool": tool_call.get("tool"),
        "data": "Operation executed successfully within safety bounds."
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)