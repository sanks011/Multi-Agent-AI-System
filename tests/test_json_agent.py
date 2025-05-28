import pytest
from agents.json_agent import JSONAgent
from memory.shared_memory import SharedMemory

def test_json_agent_process():
    # Create a context first
    memory = SharedMemory()
    thread_id = memory.save_context(
        "samples/sample_rfq.json", 
        "JSON", 
        "RFQ", 
        {"raw_text": "Sample RFQ data"}
    )
    
    agent = JSONAgent()
    reformatted, anomalies = agent.process("samples/sample_rfq.json", thread_id)
    
    # Check reformatted data (should map id->order_id, etc.)
    assert reformatted["order_id"] == "12345"
    assert reformatted["customer_name"] == "Jane Smith"
    assert reformatted["items"] == ["Product X", "Product Y"]
    assert reformatted["total_amount"] == 1500.50
    
    # Anomalies should be 0 since we have all required original fields
    assert len(anomalies) == 0