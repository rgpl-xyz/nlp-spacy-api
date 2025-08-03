#!/usr/bin/env python3
"""
Simple test script to verify the API endpoints are working correctly.
"""

import requests
import json

def test_endpoint(endpoint, data):
    """Test an endpoint and print the response."""
    print(f"\nTesting {endpoint}...")
    print(f"Request data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(f"http://localhost:8080/{endpoint}", json=data)
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def main():
    """Run simple tests."""
    print("🧪 Simple API Test")
    print("=" * 50)
    
    # Test data
    test_data = {
        "values": [
            {
                "recordId": "test_1",
                "data": {
                    "text": "Apple Inc. is headquartered in Cupertino, California.",
                    "language": "en"
                }
            }
        ]
    }
    
    # Test each endpoint
    endpoints = ["entities", "noun_phrases", "extract_all"]
    
    for endpoint in endpoints:
        success = test_endpoint(endpoint, test_data)
        if success:
            print(f"✅ {endpoint} endpoint working")
        else:
            print(f"❌ {endpoint} endpoint failed")
    
    # Test health endpoint
    print(f"\nTesting health endpoint...")
    try:
        response = requests.get("http://localhost:8080/health")
        print(f"Health status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.json()}")
        else:
            print(f"Health error: {response.text}")
    except Exception as e:
        print(f"Health exception: {e}")

if __name__ == "__main__":
    main() 