from memory.shared_memory import SharedMemory
from services.llm_service import LLMService
import re
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, filename='output_logs/email_agent.log')

class EmailAgent:
    def __init__(self):
        self.memory = SharedMemory()
        self.llm_service = LLMService()
        logging.info("Initialized EmailAgent with LLM service")

    def process(self, email_content, thread_id):
        try:
            # Extract email data using LLM
            extracted_data = self.llm_service.extract_email_fields(email_content)
            
            # Fallback extraction if LLM fails
            if not extracted_data:
                extracted_data = self._fallback_email_extraction(email_content)
            
            # Format for CRM
            crm_data = {
                "sender": extracted_data.get('sender', 'unknown'),
                "subject": extracted_data.get('subject', 'No subject'),
                "content": email_content[:500],  # Truncate content
                "urgency": extracted_data.get('urgency_level', 'Medium'),
                "sentiment": extracted_data.get('sentiment', 'Neutral'),
                "key_entities": extracted_data.get('key_entities', [])
            }
              # Update memory with extracted data
            self.memory.update_context(thread_id, {
                'email_extracted_data': crm_data,
                'email_content_length': len(email_content)
            })
            
            logging.info(f"Processed email for thread_id: {thread_id}")
            return crm_data

        except Exception as e:
            logging.error(f"Email processing error: {e}")
            # Ultimate fallback
            fallback_data = self._fallback_email_extraction(email_content)
            return {
                "sender": fallback_data.get('sender', 'unknown'),
                "subject": fallback_data.get('subject', 'No subject'),
                "content": email_content[:500],
                "urgency": fallback_data.get('urgency_level', 'Medium'),
                "sentiment": "Neutral",
                "key_entities": [],
                "error": str(e)
            }

    def _fallback_email_extraction(self, email_content):
        """Fallback email extraction using regex"""
        import re
        
        sender_match = re.search(r'From:\s*([^\n]+)', email_content)
        subject_match = re.search(r'Subject:\s*([^\n]+)', email_content)
        
        urgency = "Low"
        if any(word in email_content.lower() for word in ["urgent", "asap", "immediately", "rush"]):
            urgency = "High"
        elif any(word in email_content.lower() for word in ["soon", "quickly", "priority"]):
            urgency = "Medium"
            
        return {
            "sender": sender_match.group(1).strip() if sender_match else "unknown",
            "subject": subject_match.group(1).strip() if subject_match else "No subject",
            "urgency_level": urgency,
            "key_entities": [],
            "sentiment": "Neutral"
        }