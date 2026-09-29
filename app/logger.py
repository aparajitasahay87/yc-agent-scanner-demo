# app/logger.py
import json
import logging

# Configure file handler for audit logging to persistent storage
logging.basicConfig(
    filename="audit.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_audit_event(audit_record: dict):
    """
    Persists every agent enforcement decision (ALLOW/DENY) 
    to a local audit log file and streams it to the console.
    """
    log_message = json.dumps(audit_record)
    
    # Write to audit.log file on disk
    logging.info(log_message)
    
    # Print to console for immediate visibility during the demo
    print(f"\n[AUDIT LOG] -> {log_message}\n")