#!/usr/bin/env python3
"""
Demo Output Generator for Multi-Agent AI System
This script processes all sample files and generates comprehensive output logs
for demonstration purposes.
"""

import requests
import json
import os
import time
from datetime import datetime
import base64

class DemoOutputGenerator:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.demo_results = []
        
    def wait_for_server(self, max_attempts=30):
        """Wait for the server to be ready"""
        print("🔄 Waiting for server to be ready...")
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    return True
            except requests.exceptions.ConnectionError:
                if attempt < max_attempts - 1:
                    print(f"   Attempt {attempt + 1}/{max_attempts} - Server not ready, waiting...")
                    time.sleep(2)
                else:
                    print("❌ Server failed to start within timeout period")
                    return False
        return False
    
    def process_email_file(self, file_path, description):
        """Process an email file"""
        print(f"\n📧 Processing Email: {description}")
        print(f"   File: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                email_content = f.read()
            
            # Send to process_api endpoint
            response = requests.post(
                f"{self.base_url}/process_api",
                json={"input_data": email_content, "source": file_path}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Classification: {result.get('classification', 'Unknown')}")
                print(f"   📝 Intent: {result.get('intent', 'Unknown')}")
                
                # Store demo result
                demo_result = {
                    "timestamp": datetime.now().isoformat(),
                    "file_type": "email",
                    "file_path": file_path,
                    "description": description,
                    "input_preview": email_content[:200] + "..." if len(email_content) > 200 else email_content,
                    "response": result,
                    "status": "success"
                }
                self.demo_results.append(demo_result)
                
                return result
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error processing email: {str(e)}")
            return None
    
    def process_json_file(self, file_path, description):
        """Process a JSON file"""
        print(f"\n📄 Processing JSON: {description}")
        print(f"   File: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_content = f.read()
            
            # Send to process_api endpoint
            response = requests.post(
                f"{self.base_url}/process_api",
                json={"input_data": json_content, "source": "api_call"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Classification: {result.get('classification', 'Unknown')}")
                print(f"   📝 Intent: {result.get('intent', 'Unknown')}")
                
                # Store demo result
                demo_result = {
                    "timestamp": datetime.now().isoformat(),
                    "file_type": "json",
                    "file_path": file_path,
                    "description": description,
                    "input_preview": json_content[:200] + "..." if len(json_content) > 200 else json_content,
                    "response": result,
                    "status": "success"
                }
                self.demo_results.append(demo_result)
                
                return result
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error processing JSON: {str(e)}")
            return None
    
    def process_pdf_file(self, file_path, description):
        """Process a PDF file"""
        print(f"\n📑 Processing PDF: {description}")
        print(f"   File: {file_path}")
        
        try:
            # Read PDF file as binary and encode to base64
            with open(file_path, 'rb') as f:
                pdf_content = f.read()
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Send to process_api endpoint with base64 PDF
            response = requests.post(
                f"{self.base_url}/process_api",
                json={"input_data": pdf_base64, "source": "file_upload"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Classification: {result.get('classification', 'Unknown')}")
                print(f"   📝 Intent: {result.get('intent', 'Unknown')}")
                
                # Store demo result
                demo_result = {
                    "timestamp": datetime.now().isoformat(),
                    "file_type": "pdf",
                    "file_path": file_path,
                    "description": description,
                    "input_preview": f"PDF file ({len(pdf_content)} bytes)",
                    "response": result,
                    "status": "success"
                }
                self.demo_results.append(demo_result)
                
                return result
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error processing PDF: {str(e)}")
            return None
    
    def test_memory_functionality(self):
        """Test the shared memory functionality"""
        print(f"\n🧠 Testing Memory Functionality")
        
        try:
            # Get memory status
            response = requests.get(f"{self.base_url}/contexts")
            if response.status_code == 200:
                memory_status = response.json()
                print(f"   ✅ Memory Status: {memory_status}")
                
                # Store demo result
                demo_result = {
                    "timestamp": datetime.now().isoformat(),
                    "test_type": "memory_status",
                    "description": "Memory functionality test",
                    "response": memory_status,
                    "status": "success"
                }
                self.demo_results.append(demo_result)
                
                return memory_status
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error testing memory: {str(e)}")
            return None
    
    def generate_demo_report(self):
        """Generate a comprehensive demo report"""
        print(f"\n📊 Generating Demo Report...")
        
        # Create output directory
        output_dir = "demo_outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed demo results
        demo_file = f"{output_dir}/demo_results_{timestamp}.json"
        with open(demo_file, 'w', encoding='utf-8') as f:
            json.dump(self.demo_results, f, indent=2, ensure_ascii=False)
        
        # Generate summary report
        summary = {
            "demo_timestamp": datetime.now().isoformat(),
            "total_files_processed": len([r for r in self.demo_results if r.get('file_type')]),
            "successful_classifications": len([r for r in self.demo_results if r.get('status') == 'success' and r.get('file_type')]),
            "file_types_tested": list(set([r.get('file_type') for r in self.demo_results if r.get('file_type')])),
            "memory_tests": len([r for r in self.demo_results if r.get('test_type') == 'memory_status']),
            "sample_outputs": self.demo_results[:3]  # First 3 results as samples
        }
        
        summary_file = f"{output_dir}/demo_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Generate markdown report
        markdown_report = self.generate_markdown_report(summary)
        markdown_file = f"{output_dir}/demo_report_{timestamp}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        print(f"   ✅ Demo results saved to: {demo_file}")
        print(f"   ✅ Summary saved to: {summary_file}")
        print(f"   ✅ Markdown report saved to: {markdown_file}")
        
        return {
            "demo_file": demo_file,
            "summary_file": summary_file,
            "markdown_file": markdown_file
        }
    
    def generate_markdown_report(self, summary):
        """Generate a markdown demo report"""
        report = f"""# Multi-Agent AI System - Demo Report

**Generated:** {summary['demo_timestamp']}

## 📊 Demo Summary

- **Total Files Processed:** {summary['total_files_processed']}
- **Successful Classifications:** {summary['successful_classifications']}
- **File Types Tested:** {', '.join(summary['file_types_tested'])}
- **Memory Tests:** {summary['memory_tests']}

## 🎯 Test Results

### File Processing Results

"""
        
        for i, result in enumerate(self.demo_results, 1):
            if result.get('file_type'):
                report += f"""#### Test {i}: {result['description']}

- **File Type:** {result['file_type'].upper()}
- **File Path:** `{result['file_path']}`
- **Status:** {'✅ Success' if result['status'] == 'success' else '❌ Failed'}
- **Classification:** {result['response'].get('classification', 'N/A')}
- **Intent:** {result['response'].get('intent', 'N/A')}
- **Agent Used:** {result['response'].get('agent_used', 'N/A')}

**Input Preview:**
```
{result['input_preview']}
```

**Full Response:**
```json
{json.dumps(result['response'], indent=2)}
```

---

"""
        
        report += f"""## 🧠 Memory System Status

"""
        
        for result in self.demo_results:
            if result.get('test_type') == 'memory_status':
                report += f"""
**Memory Status:**
```json
{json.dumps(result['response'], indent=2)}
```
"""
        
        report += f"""
## 🔧 System Information

- **API Base URL:** {self.base_url}
- **Demo Script:** generate_demo_outputs.py
- **Output Directory:** demo_outputs/

## 📁 Sample Files Used

### Email Files
- service_complaint.eml - Customer service complaint
- urgent_product_inquiry.eml - Product inquiry email

### JSON Files  
- equipment_rfq.json - Equipment request for quotation
- invoice_data.json - Invoice processing data

### PDF Files
- invoice_example.pdf - Sample business invoice

## 🎥 Video Demo

*[Video demo to be recorded showing the system processing these files]*

---

*Generated by Multi-Agent AI System Demo Generator*
"""
        
        return report
    
    def run_full_demo(self):
        """Run the complete demo"""
        print("🚀 Starting Multi-Agent AI System Demo")
        print("="*50)
        
        # Wait for server to be ready
        if not self.wait_for_server():
            print("❌ Demo failed: Server not available")
            return False
        
        # Process sample files
        sample_files = [
            {
                "path": "sample_files/email/service_complaint.eml",
                "type": "email",
                "description": "Customer Service Complaint Email"
            },
            {
                "path": "sample_files/email/urgent_product_inquiry.eml", 
                "type": "email",
                "description": "Urgent Product Inquiry Email"
            },
            {
                "path": "sample_files/json/equipment_rfq.json",
                "type": "json", 
                "description": "Equipment Request for Quotation (JSON)"
            },
            {
                "path": "sample_files/json/invoice_data.json",
                "type": "json",
                "description": "Invoice Processing Data (JSON)"
            },
            {
                "path": "sample_files/pdf/invoice_example.pdf",
                "type": "pdf",
                "description": "Business Invoice (PDF)"
            }
        ]
        
        # Process each sample file
        for file_info in sample_files:
            file_path = file_info["path"]
            if os.path.exists(file_path):
                if file_info["type"] == "email":
                    self.process_email_file(file_path, file_info["description"])
                elif file_info["type"] == "json":
                    self.process_json_file(file_path, file_info["description"])
                elif file_info["type"] == "pdf":
                    self.process_pdf_file(file_path, file_info["description"])
            else:
                print(f"⚠️  File not found: {file_path}")
        
        # Test memory functionality
        self.test_memory_functionality()
        
        # Generate demo report
        report_files = self.generate_demo_report()
        
        print("\n🎉 Demo Complete!")
        print("="*50)
        print("📋 Demo Results:")
        print(f"   • {len([r for r in self.demo_results if r.get('file_type')])} files processed")
        print(f"   • {len([r for r in self.demo_results if r.get('status') == 'success'])} successful operations")
        print(f"   • Reports generated in demo_outputs/")
        
        return True

if __name__ == "__main__":
    # Change to the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    demo = DemoOutputGenerator()
    demo.run_full_demo()
