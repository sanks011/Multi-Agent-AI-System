import pytest
from agents.classifier_agent import ClassifierAgent

def test_classifier_detect_format():
    classifier = ClassifierAgent()
    assert classifier.detect_format("test.pdf", "test.pdf") == "PDF"
    assert classifier.detect_format("test.json", "test.json") == "JSON"
    assert classifier.detect_format("From: test@example.com", "test.txt") == "Email"

def test_classifier_extract_text():
    classifier = ClassifierAgent()
    with open("samples/sample_email.txt", "r") as f:
        text = classifier.extract_text(f.read(), "Email")
        assert "From: customer@example.com" in text