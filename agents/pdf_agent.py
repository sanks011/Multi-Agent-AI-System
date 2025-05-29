import pdfplumber
import PyPDF2
import base64
import io
import logging
from memory.shared_memory import SharedMemory
from services.llm_service import LLMService
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, filename='output_logs/pdf_agent.log')

class PDFAgent:
    def __init__(self):
        self.memory = SharedMemory()
        self.llm_service = LLMService()
        logging.info("Initialized PDF Agent")

    def process(self, input_data, thread_id):
        try:
            # Handle both file paths and base64 encoded PDFs
            text = self._extract_text_with_fallback(input_data)
            
            if not text or text.strip() == "":
                raise ValueError("No text could be extracted from PDF")

            # Get context to understand intent
            context = self.memory.get_context(thread_id)
            if not context:
                raise ValueError(f"No context found for thread_id: {thread_id}")

            intent = context.get('intent', 'Invoice')
            logging.info(f"Processing PDF with intent: {intent}")

            # Extract key fields using LLM first
            try:
                extracted_data = self.llm_service.extract_pdf_fields(text, intent)
                if extracted_data and isinstance(extracted_data, dict):
                    logging.info("Successfully extracted data using LLM")
                else:
                    raise ValueError("LLM extraction returned empty or invalid data")
            except Exception as llm_error:
                logging.warning(f"LLM extraction failed: {llm_error}, falling back to regex")
                extracted_data = self.extract_fields_fallback(text, intent)

            # Update memory with extracted data
            self.memory.update_context(thread_id, {
                'pdf_extracted_data': extracted_data,
                'pdf_text_length': len(text),
                'pdf_text_preview': text[:500]  # Store first 500 chars for debugging
            })

            logging.info(f"Successfully processed PDF for thread_id: {thread_id}")
            return extracted_data

        except Exception as e:
            logging.error(f"PDF processing error: {e}")
            
            # Enhanced fallback - try to extract some basic info
            try:
                text = self._extract_text_with_fallback(input_data)
                if text:
                    fallback_data = self.extract_fields_fallback(text, "Invoice")
                    fallback_data['processing_status'] = 'fallback_used'
                    fallback_data['original_error'] = str(e)
                    return fallback_data
            except Exception as fallback_error:
                logging.error(f"Fallback also failed: {fallback_error}")
            
            return {
                "error": "Failed to process PDF", 
                "details": str(e),
                "processing_status": "failed"
            }

    def _extract_text_with_fallback(self, input_data):
        """Extract text using multiple methods with robust fallback"""
        
        # Method 1: Try pdfplumber first (usually better for text extraction)
        try:
            text = self._extract_with_pdfplumber(input_data)
            if text and text.strip():
                logging.info("Successfully extracted text using pdfplumber")
                return text
        except Exception as e:
            logging.warning(f"pdfplumber failed: {e}")

        # Method 2: Fallback to PyPDF2
        try:
            text = self._extract_with_pypdf2(input_data)
            if text and text.strip():
                logging.info("Successfully extracted text using PyPDF2")
                return text
        except Exception as e:
            logging.warning(f"PyPDF2 failed: {e}")

        # Method 3: Try to read as raw text if it's a file
        try:
            if isinstance(input_data, str) and not self._is_base64(input_data):
                with open(input_data, 'rb') as f:
                    # Try to read first few bytes to see if it's actually a PDF
                    header = f.read(10)
                    if header.startswith(b'%PDF'):
                        f.seek(0)
                        # Try a different approach
                        content = f.read()
                        text_content = content.decode('latin-1', errors='ignore')
                        # Extract readable text using simple pattern matching
                        import re
                        text_matches = re.findall(r'\((.*?)\)', text_content)
                        if text_matches:
                            extracted = ' '.join(text_matches)
                            if len(extracted) > 50:  # Reasonable amount of text
                                logging.info("Extracted text using raw PDF parsing")
                                return extracted
        except Exception as e:
            logging.warning(f"Raw text extraction failed: {e}")

        raise ValueError("All text extraction methods failed")

    def _extract_with_pdfplumber(self, input_data):
        """Extract text using pdfplumber"""
        if isinstance(input_data, str) and not self._is_base64(input_data):
            # File path
            with pdfplumber.open(input_data) as pdf:
                return self._extract_pages_text(pdf.pages)
        else:
            # Base64 encoded PDF
            pdf_bytes = self._decode_base64_pdf(input_data)
            pdf_stream = io.BytesIO(pdf_bytes)
            with pdfplumber.open(pdf_stream) as pdf:
                return self._extract_pages_text(pdf.pages)

    def _extract_with_pypdf2(self, input_data):
        """Extract text using PyPDF2"""
        if isinstance(input_data, str) and not self._is_base64(input_data):
            # File path
            with open(input_data, 'rb') as file:
                return self._extract_pypdf2_text(file)
        else:
            # Base64 encoded PDF
            pdf_bytes = self._decode_base64_pdf(input_data)
            pdf_stream = io.BytesIO(pdf_bytes)
            return self._extract_pypdf2_text(pdf_stream)

    def _extract_pages_text(self, pages):
        """Extract text from pages with error handling"""
        text = ""
        successful_pages = 0
        
        for page_num, page in enumerate(pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text += page_text + "\n"
                    successful_pages += 1
                    logging.debug(f"Extracted text from page {page_num + 1}")
            except Exception as e:
                logging.warning(f"Error extracting text from page {page_num + 1}: {e}")
                continue
        
        if successful_pages > 0:
            logging.info(f"Successfully extracted text from {successful_pages} pages")
            return text.strip()
        else:
            raise ValueError("No text could be extracted from any pages")

    def _extract_pypdf2_text(self, pdf_source):
        """Extract text using PyPDF2 with error handling"""
        reader = PyPDF2.PdfReader(pdf_source)
        
        # Handle encrypted PDFs
        if reader.is_encrypted:
            logging.info("PDF is encrypted, attempting to decrypt")
            success = reader.decrypt("")
            if not success:
                raise ValueError("PDF is encrypted and cannot be decrypted")

        text = ""
        successful_pages = 0
        
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text += page_text + "\n"
                    successful_pages += 1
            except Exception as e:
                logging.warning(f"PyPDF2: Error extracting text from page {page_num + 1}: {e}")
                continue

        if successful_pages > 0:
            logging.info(f"PyPDF2: Successfully extracted text from {successful_pages} pages")
            return text.strip()
        else:
            raise ValueError("PyPDF2: No text could be extracted from any pages")

    def _decode_base64_pdf(self, base64_data):
        """Decode base64 PDF data with validation"""
        try:
            # Clean the input
            cleaned_data = base64_data.strip()
            
            # Remove data URL prefix if present
            if cleaned_data.startswith('data:'):
                if ',' in cleaned_data:
                    cleaned_data = cleaned_data.split(',', 1)[1]
            
            # Add padding if needed
            padding_needed = 4 - (len(cleaned_data) % 4)
            if padding_needed != 4:
                cleaned_data += '=' * padding_needed
            
            # Decode
            decoded_pdf = base64.b64decode(cleaned_data)
            
            # Validate PDF header
            if len(decoded_pdf) < 5 or not decoded_pdf.startswith(b'%PDF'):
                raise ValueError("Invalid PDF: Missing PDF header")
            
            return decoded_pdf
            
        except Exception as e:
            raise ValueError(f"Failed to decode base64 PDF: {e}")

    def _is_base64(self, data):
        """Check if data is base64 encoded"""
        if not isinstance(data, str):
            return False
        
        # Check for file path patterns
        if '/' in data or '\\' in data or data.endswith('.pdf'):
            return False
            
        # Check length and characters
        if len(data) < 20:
            return False
            
        # Basic base64 pattern check
        import re
        base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
        return bool(base64_pattern.match(data.strip()))

    def extract_fields_fallback(self, text, intent):
        """Enhanced fallback extraction using regex patterns"""
        data = {}
        
        if intent.lower() == "invoice":
            # Extract invoice number - multiple patterns
            invoice_patterns = [
                r"Invoice\s*#?\s*[:.]?\s*([A-Z0-9\-]+)",
                r"INV[-_]?(\d+)",
                r"Invoice\s+Number\s*[:.]?\s*([A-Z0-9\-]+)"
            ]
            
            for pattern in invoice_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['invoice_number'] = match.group(1)
                    break
            else:
                data['invoice_number'] = "Not Found"

            # Extract amount - multiple patterns
            amount_patterns = [
                r"Total\s*[:$]?\s*\$?([\d,]+\.?\d*)",
                r"Amount\s*[:$]?\s*\$?([\d,]+\.?\d*)",
                r"\$\s*([\d,]+\.?\d*)",
                r"(\d+\.\d{2})\s*USD"
            ]
            
            for pattern in amount_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        amount_str = match.group(1).replace(",", "")
                        data['amount'] = float(amount_str)
                        break
                    except ValueError:
                        continue
            else:
                data['amount'] = 0.0

            # Extract date - multiple patterns
            date_patterns = [
                r"Date\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"(\d{4}-\d{2}-\d{2})"
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['date'] = match.group(1)
                    break
            else:
                data['date'] = "Not Found"

        elif intent.lower() == "rfq":
            # Extract RFQ number
            rfq_patterns = [
                r"RFQ\s*#?\s*[:.]?\s*([A-Z0-9\-]+)",
                r"Request\s+for\s+Quote\s*#?\s*[:.]?\s*([A-Z0-9\-]+)"
            ]
            
            for pattern in rfq_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['rfq_number'] = match.group(1)
                    break
            else:
                data['rfq_number'] = "Not Found"

            # Extract deadline
            deadline_patterns = [
                r"Deadline\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"Due\s+Date\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
            ]
            
            for pattern in deadline_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['deadline'] = match.group(1)
                    break
            else:
                data['deadline'] = "Not Found"

        elif intent.lower() == "complaint":
            # Extract complaint-specific information
            data['complaint_type'] = "General"
            
            # Look for urgency indicators
            urgency_indicators = ['urgent', 'immediate', 'critical', 'emergency']
            if any(indicator in text.lower() for indicator in urgency_indicators):
                data['urgency'] = "High"
            else:
                data['urgency'] = "Medium"
            
            # Extract any reference numbers
            ref_match = re.search(r"Reference\s*#?\s*[:.]?\s*([A-Z0-9\-]+)", text, re.IGNORECASE)
            data['reference_number'] = ref_match.group(1) if ref_match else "Not Found"

        # Add common fields
        data['text_length'] = len(text)
        data['extraction_method'] = 'regex_fallback'
        
        return data