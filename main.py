from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from agents.classifier_agent import ClassifierAgent
from agents.json_agent import JSONAgent
from agents.email_agent import EmailAgent
from agents.pdf_agent import PDFAgent
import os
import json
import logging
import base64
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output_logs/api.log'),
        logging.StreamHandler()
    ]
)

app = FastAPI(
    title="Multi-Agent AI System",
    description="A system that processes PDF, JSON, and Email inputs using specialized agents",
    version="1.0.0"
)

# Initialize agents
try:
    classifier = ClassifierAgent()
    json_agent = JSONAgent()
    email_agent = EmailAgent()
    pdf_agent = PDFAgent()
    logging.info("All agents initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize agents: {e}")
    raise

@app.post("/process")
async def process_input(file: UploadFile = File(...)):
    try:
        # Create directories if they don't exist
        os.makedirs("samples", exist_ok=True)
        os.makedirs("output_logs", exist_ok=True)
        
        # Save uploaded file
        file_path = f"samples/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        logging.info(f"Saved file: {file_path}")

        # Process the file
        return await process_file(file_path, file.filename)

    except Exception as e:
        logging.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/process_api")
async def process_api_input(request: dict = Body(...)):
    try:
        # Create directories if they don't exist
        os.makedirs("temp", exist_ok=True)
        os.makedirs("output_logs", exist_ok=True)
        
        source = request.get("source", "input.txt")
        input_data = request.get("input_data", "")
        
        # Debug logging
        logging.info(f"API received - source: {source}, input_data type: {type(input_data)}")
        if isinstance(input_data, dict):
            logging.info(f"Input data keys: {list(input_data.keys())}")
        
        # Handle PowerShell objects that wrap content in a "value" property
        if isinstance(input_data, dict) and "value" in input_data and len(input_data) > 3:
            # This looks like a PowerShell object with metadata, extract just the value
            logging.info("Detected PowerShell object wrapper, extracting value")
            input_data = input_data["value"]
        
        # If source is a file path, just use the filename for saving
        if "/" in source:
            filename = source.split("/")[-1]
            file_path = f"temp/{filename}"
        else:
            file_path = f"temp/{source}"
        
        # Handle different input types
        if isinstance(input_data, dict):
            with open(file_path, "w") as f:
                json.dump(input_data, f)
        else:
            # Check if this might be base64 PDF data
            is_base64_pdf = False
            logging.info(f"Checking if input is base64 PDF: data_type={type(input_data)}, length={len(str(input_data))}")
            
            if isinstance(input_data, str) and len(input_data) > 100:
                # Check for PDF base64 signature and PDF file extension
                starts_with_jvberi = input_data.startswith('JVBERi')
                has_pdf_in_source = (source.lower().endswith('.pdf') or 'pdf' in source.lower())
                logging.info(f"Base64 PDF check 1: starts_with_JVBERi={starts_with_jvberi}, has_pdf_in_source={has_pdf_in_source}")
                
                if starts_with_jvberi and has_pdf_in_source:
                    is_base64_pdf = True
                    logging.info("Detected base64 PDF via signature + extension")
                # Also check if we can decode it and it starts with PDF header
                elif len(input_data) > 20:
                    try:
                        # Try to decode first 20 characters to check for PDF header
                        padded_sample = input_data[:20] + '=' * (4 - len(input_data[:20]) % 4)
                        decoded_sample = base64.b64decode(padded_sample)
                        if decoded_sample.startswith(b'%PDF'):
                            is_base64_pdf = True
                            logging.info("Detected base64 PDF via decode test")
                    except Exception as decode_test_error:
                        logging.debug(f"Base64 decode test failed: {decode_test_error}")
            
            logging.info(f"Final is_base64_pdf decision: {is_base64_pdf}")
            
            if is_base64_pdf:
                # This is base64 PDF data, decode and save as binary
                try:
                    # Add padding if needed for complete string
                    padded_data = input_data + '=' * (4 - len(input_data) % 4)
                    decoded_pdf = base64.b64decode(padded_data)
                    
                    # Verify it's actually a PDF
                    if decoded_pdf.startswith(b'%PDF'):
                        with open(file_path, "wb") as f:
                            f.write(decoded_pdf)
                        logging.info(f"Successfully decoded and saved PDF binary data to {file_path}, size: {len(decoded_pdf)}")
                    else:
                        logging.warning("Decoded data doesn't start with PDF header, saving as text")
                        with open(file_path, "w") as f:
                            f.write(str(input_data))
                except Exception as decode_error:
                    logging.error(f"Failed to decode base64 PDF: {decode_error}")
                    # Fallback to text file
                    with open(file_path, "w") as f:
                        f.write(str(input_data))
            else:
                # Regular text data
                logging.info("Saving as regular text file")
                with open(file_path, "w") as f:
                    f.write(str(input_data))
                
        # Process the file
        return await process_file(file_path, source)
        
    except Exception as e:
        logging.error(f"API processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

async def process_file(file_path: str, source: str):
    """Process a file through the multi-agent system"""
    try:
        # Classify input
        input_type, intent, thread_id = classifier.classify(file_path, source)
        logging.info(f"Classification result - Type: {input_type}, Intent: {intent}, Thread: {thread_id}")
        
        # Route to appropriate agent
        result = None
        if input_type == 'JSON':
            result = json_agent.process(file_path, thread_id)
        elif input_type == 'Email':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            result = email_agent.process(content, thread_id)
        elif input_type == 'PDF':
            result = pdf_agent.process(file_path, thread_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported input type: {input_type}")

        # Log result to file
        result_log = {
            "thread_id": thread_id,
            "type": input_type,
            "intent": intent,
            "result": result,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with open(f"output_logs/{thread_id}.json", "w") as f:
            json.dump(result_log, f, indent=2)
        logging.info(f"Logged result for thread_id: {thread_id}")

        return JSONResponse(content=result_log)
        
    except Exception as e:
        logging.error(f"File processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        redis_connected = False
        try:
            redis_connected = classifier.memory.redis_client and classifier.memory.redis_client.ping()
        except:
            pass
        
        return {
            "status": "healthy", 
            "redis_connected": redis_connected,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logging.error(f"Health check error: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/context/{thread_id}")
async def get_context(thread_id: str):
    """Get context for a specific thread ID"""
    try:
        context = classifier.memory.get_context(thread_id)
        if not context:
            raise HTTPException(status_code=404, detail="Context not found")
        return context
    except Exception as e:
        logging.error(f"Error retrieving context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/contexts")
async def get_all_contexts():
    """Get all stored contexts (for monitoring)"""
    try:
        contexts = classifier.memory.get_all_contexts()
        return {"contexts": contexts, "count": len(contexts)}
    except Exception as e:
        logging.error(f"Error retrieving all contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint - redirects to documentation"""
    return {
        "message": "Multi-Agent AI System API",
        "documentation_url": "/docs",
        "health_check": "/health",
        "endpoints": {
            "process_file": "/process",
            "process_api": "/process_api",
            "health": "/health",
            "context": "/context/{thread_id}",
            "all_contexts": "/contexts"
        }
    }
