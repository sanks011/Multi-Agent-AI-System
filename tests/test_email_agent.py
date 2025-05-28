import pytest
from agents.email_agent import EmailAgent

def test_email_agent_process():
    agent = EmailAgent()
    with open("samples/sample_email.txt", "r") as f:
        result = agent.process(f.read(), "test-thread-id")
    assert result["sender"] == "customer@example.com"