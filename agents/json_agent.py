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
        # Target schema for output standardization
        self.target_schema = {
            "order_id": str,
            "customer_name": str,
            "items": list,
            "total_amount": float
        }
        logging.info("Initialized JSON Agent with flexible schema handling")

    def process(self, input_data, thread_id):
        try:
            # Handle both file paths and direct JSON strings
            if isinstance(input_data, str) and input_data.startswith('{'):
                # Direct JSON string
                data = json.loads(input_data)
                logging.info(f"Loaded JSON data from string")
            else:
                # File path
                with open(input_data, 'r') as file:
                    data = json.load(file)
                logging.info(f"Loaded JSON data from {input_data}")

            # Detect and process JSON structure
            reformatted, anomalies = self.process_json_structure(data)

            # Update memory with processed data
            self.memory.update_context(thread_id, {
                'json_original_data': data,
                'json_reformatted_data': reformatted,
                'json_anomalies': anomalies,
                'json_structure_type': self.detect_structure_type(data)
            })
            
            logging.info(f"Processed JSON for thread_id: {thread_id}")
            
            # Return reformatted data with anomalies
            result = reformatted.copy()
            if anomalies:
                result['anomalies'] = anomalies
                
            return result

        except Exception as e:
            logging.error(f"JSON processing error: {e}")
            error_result = {
                "error": "Failed to process JSON", 
                "details": str(e),
                "order_id": "",
                "customer_name": "",
                "items": [],
                "total_amount": 0.0
            }
            
            # Try to save some context even on error
            try:
                self.memory.update_context(thread_id, {
                    'json_processing_error': str(e),
                    'json_raw_input': str(input_data)[:1000]
                })
            except:
                pass
                
            return error_result

    def detect_structure_type(self, data):
        """Detect the type of JSON structure"""
        if isinstance(data, dict):
            if "orderRequest" in data:
                return "nested_order_request"
            elif "order" in data:
                return "nested_order"
            elif any(key in data for key in ["id", "customer", "products", "total"]):
                return "flat_order"
            elif any(key in data for key in ["rfq", "request", "quote"]):
                return "rfq_structure"
            else:
                return "custom_structure"
        elif isinstance(data, list):
            return "array_structure"
        else:
            return "unknown_structure"

    def process_json_structure(self, data):
        """Process JSON based on detected structure"""
        structure_type = self.detect_structure_type(data)
        logging.info(f"Detected JSON structure type: {structure_type}")
        
        if structure_type == "nested_order_request":
            return self.process_nested_order_request(data)
        elif structure_type == "nested_order":
            return self.process_nested_order(data)
        elif structure_type == "flat_order":
            return self.process_flat_order(data)
        elif structure_type == "rfq_structure":
            return self.process_rfq_structure(data)
        elif structure_type == "array_structure":
            return self.process_array_structure(data)
        else:
            return self.process_custom_structure(data)

    def process_nested_order_request(self, data):
        """Process nested orderRequest structure (like your example)"""
        anomalies = []
        
        try:
            order_request = data.get("orderRequest", {})
            
            # Extract basic information
            order_id = str(order_request.get("id", ""))
            if not order_id:
                anomalies.append("Missing orderRequest.id")
            
            # Extract customer information
            customer = order_request.get("customer", {})
            if isinstance(customer, dict):
                customer_name = customer.get("name", "")
                if not customer_name:
                    anomalies.append("Missing customer name in orderRequest.customer")
            elif isinstance(customer, str):
                customer_name = customer
            else:
                customer_name = ""
                anomalies.append("Invalid customer format in orderRequest")
            
            # Extract items
            items = order_request.get("items", [])
            if not isinstance(items, list):
                anomalies.append("orderRequest.items should be a list")
                items = []
            elif len(items) == 0:
                anomalies.append("orderRequest.items is empty")
            
            # Process items and calculate total
            processed_items = []
            total_amount = 0.0
            
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    processed_item = {
                        "sku": item.get("sku", ""),
                        "description": item.get("description", ""),
                        "quantity": item.get("quantity", 0),
                        "unitPrice": item.get("unitPrice"),
                        "preferredSpecs": item.get("preferredSpecs", {})
                    }
                    processed_items.append(processed_item)
                    
                    # Calculate total if unit price is available
                    unit_price = item.get("unitPrice")
                    quantity = item.get("quantity", 0)
                    if unit_price is not None and isinstance(unit_price, (int, float)):
                        total_amount += float(unit_price) * int(quantity)
                else:
                    anomalies.append(f"Item {i} is not a valid object")
            
            # If no unit prices available, note it
            if total_amount == 0.0 and len(processed_items) > 0:
                anomalies.append("No unit prices available - total amount cannot be calculated")
            
            reformatted = {
                "order_id": order_id,
                "customer_name": customer_name,
                "items": processed_items,
                "total_amount": total_amount,
                "additional_info": {
                    "request_type": order_request.get("requestType", ""),
                    "date_submitted": order_request.get("dateSubmitted", ""),
                    "delivery_requirements": order_request.get("deliveryRequirements", {}),
                    "additional_notes": order_request.get("additionalNotes", "")
                }
            }
            
            return reformatted, anomalies
            
        except Exception as e:
            logging.error(f"Error processing nested order request: {e}")
            anomalies.append(f"Processing error: {str(e)}")
            return self.create_empty_result(), anomalies

    def process_nested_order(self, data):
        """Process nested order structure"""
        anomalies = []
        
        try:
            order = data.get("order", {})
            
            # Extract basic information
            order_id = str(order.get("id", ""))
            if not order_id:
                anomalies.append("Missing order.id")
            
            # Extract customer information
            customer = order.get("customer", "")
            if isinstance(customer, dict):
                customer_name = customer.get("name", "")
            else:
                customer_name = str(customer)
            
            if not customer_name:
                anomalies.append("Missing customer information")
            
            # Extract items
            items = order.get("items", order.get("products", []))
            if not isinstance(items, list):
                anomalies.append("Items should be a list")
                items = []
            
            # Calculate total
            total_amount = float(order.get("total", order.get("amount", 0.0)))
            if total_amount == 0.0:
                total_amount = self.calculate_total_from_items(items)
            
            reformatted = {
                "order_id": order_id,
                "customer_name": customer_name,
                "items": items,
                "total_amount": total_amount
            }
            
            return reformatted, anomalies
            
        except Exception as e:
            logging.error(f"Error processing nested order: {e}")
            anomalies.append(f"Processing error: {str(e)}")
            return self.create_empty_result(), anomalies

    def process_flat_order(self, data):
        """Process flat order structure"""
        anomalies = []
        
        # Original flat structure validation
        required_fields = {"id": str, "customer": str, "products": list, "total": (int, float)}
        
        for key, expected_type in required_fields.items():
            if key not in data:
                anomalies.append(f"Missing field: {key}")
            elif isinstance(expected_type, tuple):
                if not isinstance(data.get(key), expected_type):
                    anomalies.append(f"Invalid type for {key}: expected one of {expected_type}, got {type(data.get(key))}")
            elif not isinstance(data.get(key), expected_type):
                anomalies.append(f"Invalid type for {key}: expected {expected_type}, got {type(data.get(key))}")

        reformatted = {
            "order_id": str(data.get("id", "")),
            "customer_name": data.get("customer", ""),
            "items": data.get("products", []),
            "total_amount": float(data.get("total", 0.0))
        }
        
        return reformatted, anomalies

    def process_rfq_structure(self, data):
        """Process RFQ-specific structures"""
        anomalies = []
        
        # Look for RFQ-specific fields
        rfq_data = data.get("rfq", data)  # Use root if no 'rfq' key
        
        reformatted = {
            "order_id": str(rfq_data.get("rfq_number", rfq_data.get("id", ""))),
            "customer_name": rfq_data.get("vendor", rfq_data.get("customer", "")),
            "items": rfq_data.get("items", rfq_data.get("products", [])),
            "total_amount": 0.0,  # RFQs typically don't have totals initially
            "rfq_specific": {
                "deadline": rfq_data.get("deadline", ""),
                "requirements": rfq_data.get("requirements", ""),
                "specifications": rfq_data.get("specifications", {})
            }
        }
        
        if not reformatted["order_id"]:
            anomalies.append("Missing RFQ number or ID")
        if not reformatted["customer_name"]:
            anomalies.append("Missing vendor/customer information")
            
        return reformatted, anomalies

    def process_array_structure(self, data):
        """Process array of orders"""
        if len(data) == 0:
            return self.create_empty_result(), ["Empty array provided"]
        
        # Process first item in array
        first_item = data[0]
        reformatted, anomalies = self.process_json_structure(first_item)
        
        # Add note about multiple items
        if len(data) > 1:
            anomalies.append(f"Array contains {len(data)} items, processed only the first one")
            reformatted["additional_items_count"] = len(data) - 1
            
        return reformatted, anomalies

    def process_custom_structure(self, data):
        """Process unknown/custom structures by extracting common patterns"""
        anomalies = ["Unknown JSON structure - using best-effort extraction"]
        
        # Try to find common patterns
        order_id = ""
        customer_name = ""
        items = []
        total_amount = 0.0
        
        # Recursive search for common field names
        def find_field_value(obj, field_names):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in [name.lower() for name in field_names]:
                        return value
                    elif isinstance(value, (dict, list)):
                        result = find_field_value(value, field_names)
                        if result is not None:
                            return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_field_value(item, field_names)
                    if result is not None:
                        return result
            return None
        
        # Search for ID
        id_value = find_field_value(data, ["id", "order_id", "orderid", "number"])
        if id_value:
            order_id = str(id_value)
        
        # Search for customer
        customer_value = find_field_value(data, ["customer", "client", "name", "customer_name"])
        if customer_value:
            if isinstance(customer_value, dict):
                customer_name = customer_value.get("name", str(customer_value))
            else:
                customer_name = str(customer_value)
        
        # Search for items
        items_value = find_field_value(data, ["items", "products", "orders", "line_items"])
        if items_value and isinstance(items_value, list):
            items = items_value
        
        # Search for total
        total_value = find_field_value(data, ["total", "amount", "total_amount", "price"])
        if total_value and isinstance(total_value, (int, float)):
            total_amount = float(total_value)
        
        reformatted = {
            "order_id": order_id,
            "customer_name": customer_name,
            "items": items,
            "total_amount": total_amount,
            "raw_structure": data  # Include original for reference
        }
        
        return reformatted, anomalies

    def create_empty_result(self):
        """Create empty result structure"""
        return {
            "order_id": "",
            "customer_name": "",
            "items": [],
            "total_amount": 0.0
        }

    def calculate_total_from_items(self, items):
        """Calculate total from items if possible"""
        total = 0.0
        for item in items:
            if isinstance(item, dict):
                unit_price = item.get("unitPrice") or item.get("price") or item.get("unit_price")
                quantity = item.get("quantity", 1)
                
                if unit_price is not None and isinstance(unit_price, (int, float)):
                    total += float(unit_price) * int(quantity)
        return total

    def validate_structure(self, data, structure_type):
        """Validate data structure and return anomalies"""
        anomalies = []
        
        if structure_type == "nested_order_request":
            if "orderRequest" not in data:
                anomalies.append("Missing 'orderRequest' root element")
            else:
                order_req = data["orderRequest"]
                if not order_req.get("id"):
                    anomalies.append("Missing orderRequest.id")
                if not order_req.get("customer"):
                    anomalies.append("Missing orderRequest.customer")
                if not order_req.get("items"):
                    anomalies.append("Missing orderRequest.items")
        
        return anomalies