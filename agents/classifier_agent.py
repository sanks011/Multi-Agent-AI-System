import os
from dotenv import load_dotenv
import PyPDF2
import json
import logging
from memory.shared_memory import SharedMemory
from services.llm_service import LLMService

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, filename='output_logs/classifier.log')

class ClassifierAgent:
    def __init__(self):
        self.memory = SharedMemory()
        self.llm_service = LLMService()
        self.intents = ["Invoice", "RFQ", "Complaint", "Regulation", "General Inquiry"]
        logging.info("Initialized Classifier Agent with LLM service")

    def classify(self, input_data, source):
        try:
            # Detect format
            input_type = self.detect_format(input_data, source)
            logging.info(f"Detected format: {input_type}")

            # Extract text
            text = self.extract_text(input_data, input_type)
            if not text:
                raise ValueError("No text extracted from input")

            # Classify intent using LLM
            result = self.llm_service.classify_intent(text, self.intents)
            intent = result.get('intent', self.intents[0])
            confidence = result.get('confidence', 0.5)
            logging.info(f"Classified intent: {intent} (confidence: {confidence:.2f})")

            # Log to memory
            thread_id = self.memory.save_context(source, input_type, intent, {
                "raw_text": text[:1000],  # Store first 1000 chars
                "classification_confidence": confidence,
                "classification_reasoning": result.get('reasoning', '')
            })
            return input_type, intent, thread_id

        except Exception as e:
            logging.error(f"Classification error: {e}")
            # Fallback classification
            try:
                input_type = self.detect_format(input_data, source)
            except:
                input_type = "Unknown"
                
            intent = self.intents[0]  # Default to first intent
            thread_id = self.memory.save_context(source, input_type, intent, {
                "raw_text": str(input_data)[:500],
                "classification_confidence": 0.1,
                "error": str(e)            })
            return input_type, intent, thread_id

    def detect_format(self, input_data, source):
        """Detect input format with improved logic"""
        try:
            # Check source file extension first
            if source.lower().endswith('.pdf'):
                return 'PDF'
            elif source.lower().endswith('.json'):
                return 'JSON'
            elif source.lower().endswith(('.eml', '.txt', '.email')):
                return 'Email'
            
            # Check if it's a file path
            elif isinstance(input_data, str) and os.path.isfile(input_data):
                _, ext = os.path.splitext(input_data)
                if ext.lower() == '.pdf':
                    return 'PDF'
                elif ext.lower() == '.json':
                    return 'JSON'
                elif ext.lower() in ['.eml', '.msg']:
                    return 'Email'
            
            # Content-based detection
            elif isinstance(input_data, str):
                # Email detection
                if ('@' in input_data or 'Subject:' in input_data or 'From:' in input_data):
                    return 'Email'
                
                # JSON detection
                try:
                    json.loads(input_data)
                    return 'JSON'
                except (json.JSONDecodeError, ValueError):
                    pass
                
                # Base64 PDF detection (for file uploads)
                if source == "file_upload" and len(input_data) > 100:
                    try:
                        import base64
                        decoded = base64.b64decode(input_data[:100])
                        if decoded.startswith(b'%PDF'):
                            return 'PDF'
                    except:
                        pass
            
            return 'Email'  # Default fallback for text content
            
        except Exception as e:
            logging.error(f"Format detection error: {e}")
            return 'Email'  # Safe fallback
    
    def extract_text(self, input_data, input_type):
        try:
            if input_type == 'PDF':
                # Check if input_data is a file path or base64 content
                if isinstance(input_data, str) and os.path.isfile(input_data):
                    # File path
                    with open(input_data, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text += extracted + " "
                        return text.strip()
                else:
                    # Base64 encoded PDF content
                    try:
                        import base64
                        import io
                        decoded_pdf = base64.b64decode(input_data)
                        pdf_stream = io.BytesIO(decoded_pdf)
                        reader = PyPDF2.PdfReader(pdf_stream)
                        text = ""
                        for page in reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text += extracted + " "
                        return text.strip()
                    except Exception as e:
                        logging.error(f"PDF base64 extraction error: {e}")
                        return f"PDF content ({len(input_data)} characters)"
                        
            elif input_type == 'JSON':
                # Check if input_data is a file path or JSON content
                if isinstance(input_data, str) and os.path.isfile(input_data):
                    # File path
                    with open(input_data, 'r') as file:
                        return json.dumps(json.load(file))
                else:
                    # Direct JSON content
                    try:
                        # Validate and format JSON
                        parsed = json.loads(input_data)
                        return json.dumps(parsed, indent=2)
                    except json.JSONDecodeError:
                        # If not valid JSON, return as text
                        return input_data
                        
            elif input_type == 'Email':
                # Check if input_data is a file path or email content
                if isinstance(input_data, str) and os.path.isfile(input_data):
                    # File path
                    with open(input_data, 'r', encoding='utf-8') as file:
                        return file.read()
                else:
                    # Direct email content
                    return input_data
                    
            return str(input_data)  # Fallback
        except Exception as e:
            logging.error(f"Text extraction error: {e}")
            return str(input_data)[:1000]  # Return truncated content as fallback