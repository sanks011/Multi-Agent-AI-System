from memory.shared_memory import SharedMemory
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, filename='output_logs/json_agent.log')

class JSONAgent:
    def __init__(self):
        self.memory = SharedMemory()
        self.target_schema = {
            "order_id": str,
            "customer_name": str,
            "items": list,
            "total_amount": float
        }
        # Original schema mapping (what we expect in input)
        self.original_schema = {
            "id": str,
            "customer": str,
            "products": list,
            "total": (int, float)
        }

    def process(self, input_data, thread_id):
        try:
            with open(input_data, 'r') as file:
                data = json.load(file)
            logging.info(f"Loaded JSON data from {input_data}")

            # Reformat and validate
            reformatted = self.reformat(data)
            anomalies = self.validate(data)

            # Update memory with processed data
            self.memory.update_context(thread_id, {
                'json_original_data': data,
                'json_reformatted_data': reformatted,
                'json_anomalies': anomalies
            })
            
            logging.info(f"Processed JSON for thread_id: {thread_id}")
            return reformatted, anomalies

        except Exception as e:
            logging.error(f"JSON processing error: {e}")
            return {"error": "Failed to process JSON", "details": str(e)}, [str(e)]

    def reformat(self, data):
        return {
            "order_id": str(data.get("id", "")),
            "customer_name": data.get("customer", ""),            "items": data.get("products", []),
            "total_amount": float(data.get("total", 0.0))
        }

    def validate(self, data):
        anomalies = []
        # Check for original field names, not target schema names
        original_fields = {"id": str, "customer": str, "products": list, "total": (int, float)}
        
        for key, type_expected in original_fields.items():
            if key not in data:
                anomalies.append(f"Missing field: {key}")
            elif isinstance(type_expected, tuple):
                # Handle multiple valid types (like int or float for total)
                if not isinstance(data.get(key), type_expected):
                    anomalies.append(f"Invalid type for {key}: expected one of {type_expected}, got {type(data.get(key))}")
            elif not isinstance(data.get(key), type_expected):
                anomalies.append(f"Invalid type for {key}: expected {type_expected}, got {type(data.get(key))}")
        return anomalies