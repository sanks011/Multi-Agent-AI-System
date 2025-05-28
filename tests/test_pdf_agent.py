import pytest
import os
from agents.pdf_agent import PDFAgent
from memory.shared_memory import SharedMemory

def test_pdf_agent_initialization():
    """Test PDF agent initializes correctly"""
    agent = PDFAgent()
    assert agent.memory is not None
    assert agent.llm_service is not None

def test_pdf_agent_process():
    """Test PDF processing with mock context"""
    agent = PDFAgent()
    
    # Create a mock context in memory
    memory = SharedMemory()
    thread_id = memory.save_context(
        "samples/sample_invoice.pdf", 
        "PDF", 
        "Invoice", 
        {"raw_text": "Invoice #INV001 Amount: $500.00"}
    )
    
    # Test processing (this will use fallback extraction if PDF doesn't exist)
    try:
        result = agent.process("samples/sample_invoice.pdf", thread_id)
        # Should return some result even if extraction fails
        assert isinstance(result, dict)
    except Exception as e:
        # If file doesn't exist, we should get a meaningful error
        assert "sample_invoice.pdf" in str(e) or "extract" in str(e).lower()

def test_pdf_agent_fallback_extraction():
    """Test fallback extraction methods"""
    agent = PDFAgent()
    
    # Test invoice extraction
    invoice_text = "Invoice #INV001 Date: 01/01/2023 Amount: $500.00"
    result = agent.extract_fields_fallback(invoice_text, "Invoice")
    
    assert result["invoice_number"] == "INV001"
    assert result["amount"] == 500.0
    assert result["date"] == "01/01/2023"
    
    # Test RFQ extraction
    rfq_text = "RFQ #RFQ123 Deadline: 12/31/2023"
    result = agent.extract_fields_fallback(rfq_text, "RFQ")
    
    assert result["rfq_number"] == "RFQ123"
    assert result["deadline"] == "12/31/2023"