#!/usr/bin/env python3
"""Smoke tests for the text completion service."""

import requests
import json
import sys
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def log_test_result(test_name: str, success: bool, details: Dict[str, Any] = None):
    """Log test results."""
    extra = {"test": test_name, "success": success}
    if details:
        extra.update(details)
    
    if success:
        logger.info("test.passed", extra=extra)
        print(f"✅ {test_name} passed")
    else:
        logger.error("test.failed", extra=extra)
        print(f"❌ {test_name} failed")


def test_api(base_url: str = "http://localhost:8000") -> bool:
    """Test health and completion endpoints."""
    
    logger.info("test.suite.started", extra={"base_url": base_url})
    print(f"Testing API at {base_url}")
    print("-" * 50)
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        success = response.status_code == 200
        
        log_test_result("Health Check", success, {
            "status_code": response.status_code,
            "response": response.json() if success else response.text
        })
        
        if success:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test_result("Health Check", False, {"error": str(e)})
        print(f"❌ Health check failed with error: {e}")
        return False
    
    print()
    
    # Test completion endpoint
    try:
        completion_request = {
            "prompt": "Provide a concise fact about the second person on the moon.",
            "max_tokens": 60,
            "temperature": 0.2,
        }

        print("🚀 Testing completion endpoint...")
        print(f"   Request: {json.dumps(completion_request, indent=2)}")
        
        logger.info("test.completion.request", extra=completion_request)

        response = requests.post(
            f"{base_url}/completions",
            headers={"Content-Type": "application/json"},
            json=completion_request,
            timeout=30,
        )

        success = response.status_code == 200
        
        if success:
            result = response.json()
            log_test_result("Completion Request", True, {
                "status_code": response.status_code,
                "response_id": result.get('id', 'N/A'),
                "output_length": len(result.get('output', '')),
                "finish_reason": result.get('finish_reason', 'N/A')
            })
            
            print("✅ Completion request successful")
            print(f"   Response ID: {result.get('id', 'N/A')}")
            print(f"   Output: {result.get('output', 'N/A')[:100]}...")
            print(f"   Finish Reason: {result.get('finish_reason', 'N/A')}")
            if result.get("usage"):
                print(f"   Usage: {result['usage']}")
        else:
            log_test_result("Completion Request", False, {
                "status_code": response.status_code,
                "response": response.text
            })
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        log_test_result("Completion Request", False, {"error": str(e)})
        print(f"❌ Completion request failed with error: {e}")
        return False
    
    print()
    logger.info("test.suite.completed", extra={"success": True})
    print("🎉 All tests passed!")
    return True


if __name__ == "__main__":
    # Allow custom base URL as command line argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    success = test_api(base_url)
    sys.exit(0 if success else 1)
