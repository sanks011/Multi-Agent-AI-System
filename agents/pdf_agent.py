import pdfplumber
from memory.shared_memory import SharedMemory
from services.llm_service import LLMService
import re
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, filename='output_logs/pdf_agent.log')

class PDFAgent:
    def __init__(self):
        self.memory = SharedMemory()
        self.llm_service = LLMService()

    def process(self, input_data, thread_id):
        try:
            with pdfplumber.open(input_data) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            
            # Get context to understand intent
            context = self.memory.get_context(thread_id)
            if not context:
                raise ValueError(f"No context found for thread_id: {thread_id}")
            
            intent = context.get('intent', 'Invoice')
            
            # Extract key fields using LLM
            extracted_data = self.llm_service.extract_pdf_fields(text, intent)
            
            # Fallback to regex if LLM fails
            if not extracted_data:
                extracted_data = self.extract_fields_fallback(text, intent)
            
            # Update memory with extracted data
            self.memory.update_context(thread_id, {
                'pdf_extracted_data': extracted_data,
                'pdf_text_length': len(text)
            })
            
            logging.info(f"Processed PDF for thread_id: {thread_id}")
            return extracted_data

        except Exception as e:
            logging.error(f"PDF processing error: {e}")
            # Fallback extraction
            try:
                with pdfplumber.open(input_data) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                fallback_data = self.extract_fields_fallback(text, "Invoice")
                return fallback_data
            except:
                return {"error": "Failed to process PDF", "details": str(e)}

    def extract_fields_fallback(self, text, intent):
        """Fallback extraction using regex patterns"""
        data = {}
        
        if intent.lower() == "invoice":
            # Extract invoice number
            invoice_match = re.search(r"Invoice\s*#?\s*(\w+)", text, re.IGNORECASE)
            data['invoice_number'] = invoice_match.group(1) if invoice_match else "Unknown"
              # Extract amount - more flexible pattern
            amount_match = re.search(r"Amount\s*[:$]?\s*\$?([\d,.]+)", text, re.IGNORECASE)
            if not amount_match:
                amount_match = re.search(r"\$\s*([\d,.]+)", text, re.IGNORECASE)
            data['amount'] = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0
            
            # Extract date
            date_match = re.search(r"Date\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text, re.IGNORECASE)
            data['date'] = date_match.group(1) if date_match else "Unknown"
            
        elif intent.lower() == "rfq":
            # Extract RFQ number
            rfq_match = re.search(r"RFQ\s*#?\s*(\w+)", text, re.IGNORECASE)
            data['rfq_number'] = rfq_match.group(1) if rfq_match else "Unknown"
            
            # Extract deadline
            deadline_match = re.search(r"Deadline\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text, re.IGNORECASE)
            data['deadline'] = deadline_match.group(1) if deadline_match else "Unknown"
        
        return data