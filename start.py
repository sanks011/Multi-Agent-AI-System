#!/usr/bin/env python3
"""
Startup script for the Multi-Agent AI System
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def check_redis_connection():
    """Check if Redis is available"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def check_environment():
    """Check environment variables and dependencies"""
    print("🔍 Checking environment...")
      # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version}")
    
    # Check required directories
    required_dirs = ['sample_files', 'output_logs', 'agents', 'memory', 'services']
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"📁 Created directory: {directory}")
        else:
            print(f"✅ Directory exists: {directory}")
    
    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("⚠️  GEMINI_API_KEY not set, using default")
    else:
        print("✅ GEMINI_API_KEY configured")
    
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def start_redis_docker():
    """Start Redis using Docker Compose"""
    print("🐳 Starting Redis with Docker...")
    try:
        subprocess.check_call(["docker-compose", "up", "-d", "redis"])
        time.sleep(5)  # Wait for Redis to start
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Redis: {e}")
        return False

def find_available_port(start_port=8000, max_port=8020):
    """Find an available port starting from start_port"""
    import socket
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Try to bind to the port - if it succeeds, the port is available
            try:
                sock.bind(('0.0.0.0', port))
                print(f"✅ Found available port: {port}")
                return port
            except OSError:
                print(f"⚠️ Port {port} is in use, trying next port")
                continue
    
    # If no port is found, return None
    print(f"❌ No available ports found in range {start_port}-{max_port}")
    return None

def start_application():
    """Start the FastAPI application"""
    port = find_available_port()
    if not port:
        print("❌ No available ports found. Exiting.")
        sys.exit(1)
        
    print(f"🚀 Starting Multi-Agent AI System on port {port}...")
    print(f"📋 Application will be available at: http://localhost:{port}")
    print(f"📚 API Documentation: http://localhost:{port}/docs")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "uvicorn", 
            "main:app", "--host", "0.0.0.0", "--port", str(port), "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start application: {e}")

def health_check():
    """Check if the application is running"""
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ Application is healthy!")
                return True
        except requests.RequestException:
            pass
        
        if i < max_retries - 1:
            time.sleep(2)
            print(f"⏳ Waiting for application to start... ({i+1}/{max_retries})")
    
    print("❌ Application health check failed")
    return False

def main():
    """Main startup sequence"""
    print("🤖 Multi-Agent AI System Startup")
    print("=" * 40)
    
    if not check_environment():
        sys.exit(1)
    
    if not install_dependencies():
        sys.exit(1)
    
    # Try to start Redis if not running
    if not check_redis_connection():
        if start_redis_docker():
            time.sleep(5)
            if not check_redis_connection():
                print("⚠️  Redis not available, using in-memory fallback")
        else:
            print("⚠️  Redis not available, using in-memory fallback")
    
    print("\n🎯 Starting application...")
    start_application()

if __name__ == "__main__":
    main()
