#!/usr/bin/env python3
"""
Performance test script to demonstrate the optimizations made to the spaCy API.
"""

import time
import requests
import json
from typing import List, Dict

# Test data
test_texts = [
    "The technology company is headquartered in Silicon Valley. The chief executive leads the organization.",
    "A major software corporation was founded by two entrepreneurs in the 1970s.",
    "The United States of America is located in North America. Washington D.C. is the capital city.",
    "A prominent business leader runs multiple innovative companies based in California.",
    "A global technology firm is a subsidiary of a larger holding company. The current CEO manages operations.",
    "An e-commerce giant was founded by an entrepreneur in Seattle, Washington.",
    "A social media platform was created by a college student at a prestigious university.",
    "A streaming entertainment company is based in California and serves millions of subscribers.",
    "A microblogging service was acquired by a billionaire entrepreneur and rebranded.",
    "A transportation technology company operates in San Francisco and connects drivers with passengers."
]

def create_test_request(texts: List[str]) -> Dict:
    """Create a test request with the given texts."""
    return {
        "values": [
            {
                "recordId": f"doc_{i}",
                "data": {
                    "text": text,
                    "language": "en"
                }
            }
            for i, text in enumerate(texts)
        ]
    }

def test_endpoint(endpoint: str, data: Dict, description: str) -> float:
    """Test an endpoint and return the time taken."""
    print(f"\nTesting {description}...")
    
    start_time = time.time()
    try:
        response = requests.post(f"http://localhost:8080/{endpoint}", json=data)
        end_time = time.time()
        
        if response.status_code == 200:
            elapsed = end_time - start_time
            print(f"✅ Success: {elapsed:.3f} seconds")
            return elapsed
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return -1
    except Exception as e:
        print(f"❌ Exception: {e}")
        return -1

def main():
    """Run performance tests."""
    print("🚀 spaCy API Performance Test")
    print("=" * 50)
    
    # Create test data
    test_request = create_test_request(test_texts)
    
    # Test individual endpoints
    print(f"Testing with {len(test_texts)} documents...")
    
    # Test entities endpoint
    entities_time = test_endpoint("entities", test_request, "Entities Extraction")
    
    # Test noun phrases endpoint
    noun_phrases_time = test_endpoint("noun_phrases", test_request, "Noun Phrases Extraction")
    
    # Test combined endpoint (optimized)
    combined_time = test_endpoint("extract_all", test_request, "Combined Extraction (Optimized)")
    
    # Calculate improvements
    if entities_time > 0 and noun_phrases_time > 0 and combined_time > 0:
        total_individual = entities_time + noun_phrases_time
        improvement = ((total_individual - combined_time) / total_individual) * 100
        
        print(f"\n📊 Performance Results:")
        print(f"Individual calls total: {total_individual:.3f}s")
        print(f"Combined call: {combined_time:.3f}s")
        print(f"Performance improvement: {improvement:.1f}%")
        
        if improvement > 0:
            print(f"✅ The optimized combined endpoint is {improvement:.1f}% faster!")
        else:
            print(f"⚠️  No significant improvement detected")
    
    # Test health endpoint
    print(f"\n🏥 Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8080/health")
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check exception: {e}")

if __name__ == "__main__":
    main() 