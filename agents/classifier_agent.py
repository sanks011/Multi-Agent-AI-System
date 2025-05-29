import os
from dotenv import load_dotenv
import PyPDF2
import json
import logging
import base64
import io
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
                "error": str(e)
            })
            return input_type, intent, thread_id

    def detect_format(self, input_data, source):
        """Detect input format with improved logic"""
        try:
            logging.info(f"Detecting format for source: {source}, data type: {type(input_data)}, data length: {len(str(input_data)) if input_data else 0}")
            
            # Priority 1: Content-based detection for file uploads
            if source == "file_upload" and isinstance(input_data, str):
                # Base64 PDF detection - multiple methods
                if len(input_data) > 20:
                    # Method 1: Check for PDF signature in base64
                    if input_data.startswith('JVBERi'):  # %PDF in base64
                        logging.info("Detected PDF from base64 signature (JVBERi)")
                        return 'PDF'
                    
                    # Method 2: Try to decode and check binary header
                    try:
                        # Add padding if needed for proper base64 decoding
                        padded_data = input_data + '=' * (4 - len(input_data) % 4)
                        decoded_sample = base64.b64decode(padded_data[:100])
                        if decoded_sample.startswith(b'%PDF'):
                            logging.info("Detected PDF from decoded base64 header")
                            return 'PDF'
                    except Exception as decode_error:
                        logging.debug(f"Base64 decode attempt failed: {decode_error}")
                        pass
                
                # If file_upload but not PDF, could be JSON or other text
                # Try JSON detection for file uploads
                try:
                    json.loads(input_data)
                    logging.info("Detected JSON from file upload content")
                    return 'JSON'
                except (json.JSONDecodeError, ValueError):
                    pass
            
            # Priority 2: Source-based detection hints
            if isinstance(source, str):
                # Check for file extensions in source
                if source.lower().endswith('.pdf'):
                    logging.info("Detected PDF from source filename extension")
                    return 'PDF'
                elif source.lower().endswith('.json'):
                    logging.info("Detected JSON from source filename extension")
                    return 'JSON'
                elif source.lower().endswith(('.eml', '.txt', '.email')):
                    logging.info("Detected Email from source filename extension")
                    return 'Email'
                
                # Check source type hints
                if 'email' in source.lower():
                    logging.info("Detected Email from source type hint")
                    return 'Email'
                elif 'json' in source.lower() or 'api' in source.lower():
                    # For api_call source, be more aggressive about JSON detection
                    if isinstance(input_data, str):
                        stripped_data = input_data.strip()
                        if stripped_data.startswith(('{', '[')):
                            try:
                                json.loads(stripped_data)
                                logging.info("Detected JSON from API call with JSON structure")
                                return 'JSON'
                            except (json.JSONDecodeError, ValueError):
                                pass
            
            # Priority 3: Check if input_data is a file path
            if isinstance(input_data, str) and os.path.isfile(input_data):
                _, ext = os.path.splitext(input_data)
                if ext.lower() == '.pdf':
                    logging.info("Detected PDF from file path extension")
                    return 'PDF'
                elif ext.lower() == '.json':
                    logging.info("Detected JSON from file path extension")
                    return 'JSON'
                elif ext.lower() in ['.eml', '.msg']:
                    logging.info("Detected Email from file path extension")
                    return 'Email'
            
            # Priority 4: Content analysis for strings
            if isinstance(input_data, str) and len(input_data.strip()) > 0:
                stripped_data = input_data.strip()
                
                # JSON detection - be more thorough
                if stripped_data.startswith(('{', '[')):
                    try:
                        parsed = json.loads(stripped_data)
                        # Additional validation - check if it's a meaningful JSON structure
                        if isinstance(parsed, (dict, list)) and len(str(parsed)) > 10:
                            logging.info("Detected JSON from content structure analysis")
                            return 'JSON'
                    except (json.JSONDecodeError, ValueError) as e:
                        logging.debug(f"JSON parsing failed: {e}")
                        pass
                
                # Email detection - comprehensive patterns
                email_indicators = [
                    'From:', 'To:', 'Subject:', 'Date:', 'Message-ID:', 'Content-Type:',
                    'Return-Path:', 'Received:', 'Reply-To:', 'X-', '@'
                ]
                if any(indicator in stripped_data for indicator in email_indicators):
                    # Additional check - make sure it's not just JSON containing email data
                    if not stripped_data.startswith(('{', '[')):
                        logging.info("Detected Email from content indicators")
                        return 'Email'
            
            # Priority 5: Smart defaults based on source
            if source == "file_upload":
                logging.warning("Could not detect format for file upload, defaulting to PDF")
                return 'PDF'
            elif source in ["api_call", "json_input"]:
                logging.warning("Could not detect format for API call, defaulting to JSON")
                return 'JSON'
            elif source in ["email_processing", "email_input"]:
                logging.warning("Could not detect format for email processing, defaulting to Email")
                return 'Email'
            else:
                logging.warning("Could not detect format, defaulting to Email")
                return 'Email'
            
        except Exception as e:
            logging.error(f"Format detection error: {e}")
            # Safe fallback based on source
            if source == "file_upload":
                return 'PDF'
            elif source in ["api_call", "json_input"]:
                return 'JSON'
            else:
                return 'Email'
    
    def extract_text(self, input_data, input_type):
        try:
            logging.info(f"Extracting text for type: {input_type}")
            
            if input_type == 'PDF':
                return self._extract_pdf_text(input_data)
            elif input_type == 'JSON':
                return self._extract_json_text(input_data)
            elif input_type == 'Email':
                return self._extract_email_text(input_data)
            else:
                # Fallback for any other type
                logging.info("Using fallback text extraction")
                return str(input_data)
                
        except Exception as e:
            logging.error(f"Text extraction error: {e}")
            # Enhanced fallback with more information
            if input_type == 'PDF':
                return f"PDF processing failed: {str(e)} (Content length: {len(str(input_data))})"
            else:
                return str(input_data)[:1000]  # Return truncated content as fallback
    
    def _extract_pdf_text(self, input_data):
        """Extract text from PDF with enhanced error handling and validation"""
        if isinstance(input_data, str) and os.path.isfile(input_data):
            # File path
            logging.info("Extracting PDF text from file path")
            with open(input_data, 'rb') as file:
                return self._read_pdf_content(file)
        else:
            # Base64 encoded PDF content
            logging.info("Extracting PDF text from base64 content")
            try:
                # Clean and validate base64
                cleaned_data = input_data.strip()
                
                # Remove any potential data URL prefix
                if cleaned_data.startswith('data:'):
                    if ',' in cleaned_data:
                        cleaned_data = cleaned_data.split(',', 1)[1]
                
                # Validate base64 format
                if not cleaned_data:
                    raise ValueError("Empty base64 data")
                
                # Add padding if needed
                padding_needed = 4 - (len(cleaned_data) % 4)
                if padding_needed != 4:
                    cleaned_data += '=' * padding_needed
                
                # Decode base64
                try:
                    decoded_pdf = base64.b64decode(cleaned_data)
                except Exception as b64_error:
                    logging.error(f"Base64 decode failed: {b64_error}")
                    raise ValueError(f"Invalid base64 encoding: {b64_error}")
                
                # Validate PDF header
                if len(decoded_pdf) < 5:
                    raise ValueError("Decoded content too short to be a valid PDF")
                
                if not decoded_pdf.startswith(b'%PDF'):
                    # Log first few bytes for debugging
                    header_preview = decoded_pdf[:20]
                    logging.error(f"Invalid PDF header. First 20 bytes: {header_preview}")
                    raise ValueError(f"Invalid PDF: Missing PDF header. Got: {header_preview[:10]}")
                
                # Additional PDF validation - check for basic PDF structure
                pdf_content = decoded_pdf.decode('latin-1', errors='ignore')
                if 'xref' not in pdf_content and 'trailer' not in pdf_content:
                    logging.warning("PDF structure may be incomplete - missing xref or trailer")
                
                pdf_stream = io.BytesIO(decoded_pdf)
                return self._read_pdf_content(pdf_stream)
                
            except Exception as e:
                logging.error(f"PDF base64 extraction error: {e}")
                # Provide more detailed error information
                error_details = {
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'content_length': len(input_data),
                    'content_preview': input_data[:50] + '...' if len(input_data) > 50 else input_data,
                    'starts_with_pdf_signature': input_data.startswith('JVBERi') if input_data else False
                }
                return f"PDF extraction failed: {json.dumps(error_details, indent=2)}"
    
    def _read_pdf_content(self, pdf_source):
        """Read PDF content from file or stream with enhanced error handling"""
        try:
            # Reset stream position if it's a BytesIO object
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
            
            reader = PyPDF2.PdfReader(pdf_source)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                logging.warning("PDF is encrypted, attempting to decrypt with empty password")
                success = reader.decrypt("")
                if not success:
                    raise ValueError("PDF is encrypted and cannot be decrypted with empty password")
            
            text = ""
            total_pages = len(reader.pages)
            logging.info(f"PDF has {total_pages} pages")
            
            if total_pages == 0:
                raise ValueError("PDF has no pages")
            
            successful_pages = 0
            for page_num, page in enumerate(reader.pages):
                try:
                    extracted = page.extract_text()
                    if extracted and extracted.strip():
                        text += extracted + "\n"
                        successful_pages += 1
                    logging.debug(f"Extracted text from page {page_num + 1}")
                except Exception as page_error:
                    logging.warning(f"Error extracting text from page {page_num + 1}: {page_error}")
                    continue
            
            extracted_text = text.strip()
            
            if extracted_text:
                logging.info(f"Successfully extracted {len(extracted_text)} characters from {successful_pages}/{total_pages} pages")
                return extracted_text
            else:
                logging.warning("No text could be extracted from any PDF pages")
                return f"PDF document ({total_pages} pages) - No readable text found. This could be a scanned PDF or contain only images."
                
        except Exception as e:
            logging.error(f"PDF reading error: {e}")
            # Provide detailed error context
            error_info = {
                'error': str(e),
                'error_type': type(e).__name__,
                'pdf_source_type': type(pdf_source).__name__
            }
            
            # Try to get file size if possible
            try:
                if hasattr(pdf_source, 'seek') and hasattr(pdf_source, 'tell'):
                    current_pos = pdf_source.tell()
                    pdf_source.seek(0, 2)  # Seek to end
                    size = pdf_source.tell()
                    pdf_source.seek(current_pos)  # Restore position
                    error_info['content_size'] = size
            except:
                pass
            
            raise ValueError(f"PDF processing failed: {json.dumps(error_info)}")
    
    def _extract_json_text(self, input_data):
        """Extract and format JSON content with flexible field mapping"""
        if isinstance(input_data, str) and os.path.isfile(input_data):
            # File path
            logging.info("Extracting JSON from file path")
            with open(input_data, 'r', encoding='utf-8') as file:
                content = file.read()
                parsed = json.loads(content)
                return self._format_json_for_classification(parsed)
        else:
            # Direct JSON content
            logging.info("Processing direct JSON content")
            try:
                # Clean the input
                cleaned_input = input_data.strip()
                # Validate and format JSON
                parsed = json.loads(cleaned_input)
                formatted_output = self._format_json_for_classification(parsed)
                logging.info(f"Successfully parsed JSON with {len(formatted_output)} characters")
                return formatted_output
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON format: {e}")
                # Return the original content if JSON parsing fails
                return input_data
    
    def _format_json_for_classification(self, json_data):
        """Format JSON data for better classification, handling nested structures"""
        try:
            # Create a flattened, readable version for classification
            formatted_lines = []
            
            def extract_key_info(obj, prefix=""):
                """Recursively extract key information from JSON"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_key = f"{prefix}.{key}" if prefix else key
                        
                        if isinstance(value, (dict, list)):
                            extract_key_info(value, current_key)
                        else:
                            # Format key-value pairs for readability
                            formatted_lines.append(f"{current_key}: {value}")
                            
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            extract_key_info(item, f"{prefix}[{i}]")
                        else:
                            formatted_lines.append(f"{prefix}[{i}]: {item}")
            
            # Extract information
            extract_key_info(json_data)
            
            # Also include the original formatted JSON
            original_json = json.dumps(json_data, indent=2)
            
            # Combine both for comprehensive classification
            classification_text = f"""
STRUCTURED DATA ANALYSIS:
{chr(10).join(formatted_lines)}

ORIGINAL JSON STRUCTURE:
{original_json}
"""
            
            return classification_text.strip()
            
        except Exception as e:
            logging.error(f"Error formatting JSON for classification: {e}")
            # Fallback to simple JSON dump
            return json.dumps(json_data, indent=2)
    
    def _extract_email_text(self, input_data):
        """Extract email content"""
        if isinstance(input_data, str) and os.path.isfile(input_data):
            # File path
            logging.info("Extracting email from file path")
            with open(input_data, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            # Direct email content
            logging.info("Processing direct email content")
            return input_data