# database.py

DATABASE_STORE = {
    101: {"id": 101, "owner": "alice", "tenant": "Acme", "data": "Alice's confidential project notes"},
    102: {"id": 102, "owner": "bob", "tenant": "Acme", "data": "Bob's private financial records"},
    103: {"id": 103, "owner": "charlie", "tenant": "Globex", "data": "Globex enterprise logs"}
}

def query_database(record_id: int, user_id: str):
    record = DATABASE_STORE.get(record_id)
    if not record:
        return {"error": "Record not found"}, 404
    return record, 200