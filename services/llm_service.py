# LLM service using Gemini API
import requests
import json
import os
from typing import Dict, Any
import logging

class LLMService:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyBUreDq4nkfHM9oycP_WzJYKhYAEU0_YFY')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    def classify_intent(self, text: str, possible_intents: list) -> Dict[str, Any]:
        """Classify intent using Gemini API"""
        prompt = f"""
        Analyze the following text and classify it into one of these specific categories: {', '.join(possible_intents)}

        Guidelines:
        - "RFQ" for Request for Quotation, procurement requests, product inquiries
        - "Complaint" for service issues, dissatisfaction, problems, complaints  
        - "Invoice" for billing documents, payment requests, financial statements
        - "Regulation" for compliance, policy, regulatory documents
        - "General Inquiry" for questions, general information requests

        Text to classify: {text[:1000]}
        
        Respond ONLY with valid JSON in this exact format:
        {{
            "intent": "one_of_the_categories_exactly_as_listed", 
            "confidence": 0.95,
            "reasoning": "brief explanation"
        }}
        """
        
        try:
            response = self._call_gemini(prompt)
            # Parse the response to extract JSON
            content = response.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Validate intent is in the list
                if result.get('intent') in possible_intents:
                    return result
            
            # Fallback classification based on keywords
            return self._fallback_intent_classification(text, possible_intents)
                
        except Exception as e:
            logging.error(f"LLM classification error: {e}")
            return self._fallback_intent_classification(text, possible_intents)
    
    def _fallback_intent_classification(self, text: str, possible_intents: list) -> Dict[str, Any]:
        """Fallback intent classification using keywords"""
        text_lower = text.lower()
        
        # Keyword-based classification
        if any(keyword in text_lower for keyword in ["complaint", "dissatisfied", "problem", "issue", "error", "wrong", "bad", "terrible", "awful", "unacceptable"]):
            return {"intent": "Complaint", "confidence": 0.8, "reasoning": "Keyword-based: complaint indicators"}
        
        elif any(keyword in text_lower for keyword in ["quote", "quotation", "rfq", "request", "inquiry", "product", "purchase", "buy", "pricing", "cost"]):
            return {"intent": "RFQ", "confidence": 0.8, "reasoning": "Keyword-based: request/inquiry indicators"}
        
        elif any(keyword in text_lower for keyword in ["invoice", "bill", "payment", "charge", "amount", "total", "due", "paid", "$", "price"]):
            return {"intent": "Invoice", "confidence": 0.8, "reasoning": "Keyword-based: financial/billing indicators"}
        
        elif any(keyword in text_lower for keyword in ["regulation", "compliance", "policy", "rule", "law", "requirement"]):
            return {"intent": "Regulation", "confidence": 0.8, "reasoning": "Keyword-based: regulatory indicators"}
        
        else:
            return {"intent": "General Inquiry", "confidence": 0.6, "reasoning": "Keyword-based: default classification"}
    
    def extract_email_fields(self, email_content: str) -> Dict[str, Any]:
        """Extract structured data from email using Gemini"""
        prompt = f"""
        Extract key information from this email and return as JSON:
        
        Email: {email_content}
        
        Extract:
        - sender (email address)
        - subject
        - urgency_level (Low/Medium/High)
        - key_entities (people, products, dates, amounts)
        - sentiment (Positive/Negative/Neutral)
        
        Return JSON format:
        {{
            "sender": "email@example.com",
            "subject": "extracted subject",
            "urgency_level": "Medium",
            "key_entities": ["entity1", "entity2"],
            "sentiment": "Neutral"
        }}
        """
        
        try:
            response = self._call_gemini(prompt)
            content = response.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._fallback_email_extraction(email_content)
                
        except Exception as e:
            logging.error(f"Email extraction error: {e}")
            return self._fallback_email_extraction(email_content)
    
    def extract_pdf_fields(self, pdf_text: str, intent: str) -> Dict[str, Any]:
        """Extract structured data from PDF based on intent"""
        prompt = f"""
        Extract relevant information from this {intent} document:
        
        Text: {pdf_text[:2000]}
        
        For {intent} documents, extract appropriate fields and return as JSON.
        
        Common fields to look for:
        - invoice_number, amount, date, vendor (for invoices)
        - request_id, items, quantities, deadline (for RFQs)
        - case_number, complainant, issue (for complaints)
        
        Return JSON format with relevant fields.
        """
        
        try:
            response = self._call_gemini(prompt)
            content = response.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._fallback_pdf_extraction(pdf_text, intent)
                
        except Exception as e:
            logging.error(f"PDF extraction error: {e}")
            return self._fallback_pdf_extraction(pdf_text, intent)
    
    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Make API call to Gemini"""
        url = f"{self.base_url}?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    def _fallback_email_extraction(self, email_content: str) -> Dict[str, Any]:
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
    
    def _fallback_pdf_extraction(self, pdf_text: str, intent: str) -> Dict[str, Any]:
        """Fallback PDF extraction using regex"""
        import re
        
        data = {}
        
        if intent.lower() == "invoice":
            invoice_match = re.search(r"Invoice\s*#?\s*(\w+)", pdf_text, re.IGNORECASE)
            amount_match = re.search(r"Amount\s*[:$]?\s*([\d,.]+)", pdf_text, re.IGNORECASE)
            data['invoice_number'] = invoice_match.group(1) if invoice_match else "Unknown"
            data['amount'] = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0
            
        elif intent.lower() == "rfq":
            rfq_match = re.search(r"RFQ\s*#?\s*(\w+)", pdf_text, re.IGNORECASE)
            data['rfq_number'] = rfq_match.group(1) if rfq_match else "Unknown"
            
        return data
