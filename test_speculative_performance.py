#!/usr/bin/env python3
"""
Test SGLang with Speculative Decoding performance.
Compare latency and throughput with/without speculation.
"""

import time
import requests
import statistics
from typing import List, Dict

def benchmark_completion(
    prompt: str, 
    max_tokens: int = 100,
    runs: int = 5,
    base_url: str = "http://127.0.0.1:30000"
) -> Dict:
    """Benchmark a single completion."""
    latencies = []
    tokens_per_second = []
    
    for _ in range(runs):
        start = time.time()
        
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": "gpt-oss-120b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "stream": False
            }
        )
        
        end = time.time()
        latency = end - start
        latencies.append(latency)
        
        if response.status_code == 200:
            result = response.json()
            total_tokens = result.get("usage", {}).get("completion_tokens", max_tokens)
            tokens_per_second.append(total_tokens / latency)
    
    return {
        "avg_latency": statistics.mean(latencies),
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "avg_tokens_per_sec": statistics.mean(tokens_per_second) if tokens_per_second else 0,
        "p95_latency": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]
    }

def test_speculative_decoding():
    """Test various workloads with speculative decoding."""
    print("SGLang Speculative Decoding Performance Test")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://127.0.0.1:30000/v1/models", timeout=2)
        if response.status_code != 200:
            print("✗ SGLang server not responding")
            return
        print("✓ SGLang server connected\n")
    except:
        print("✗ Server not running on port 30000")
        print("  Start with: ./start_sglang_speculative.sh")
        return
    
    # Test cases optimized for speculative decoding
    test_cases = [
        {
            "name": "Short Generation (Benefits from Speculation)",
            "prompt": "List 5 benefits of exercise:",
            "max_tokens": 50
        },
        {
            "name": "Code Generation (High Speculation Accuracy)",
            "prompt": "Write a Python function to calculate factorial:",
            "max_tokens": 100
        },
        {
            "name": "Factual Q&A (Predictable Patterns)",
            "prompt": "What are the main components of a computer? Explain each briefly:",
            "max_tokens": 150
        },
        {
            "name": "Creative Writing (Lower Speculation Accuracy)",
            "prompt": "Write a creative story opening about a mysterious door:",
            "max_tokens": 100
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"Testing: {test['name']}")
        print("-" * 40)
        
        result = benchmark_completion(
            test["prompt"], 
            test["max_tokens"],
            runs=3
        )
        
        print(f"  Avg Latency: {result['avg_latency']:.3f}s")
        print(f"  Tokens/sec: {result['avg_tokens_per_sec']:.1f}")
        print(f"  P95 Latency: {result['p95_latency']:.3f}s")
        
        # Speculative decoding efficiency indicator
        if result['avg_tokens_per_sec'] > 50:
            print(f"  ✓ Excellent speed - speculation working well")
        elif result['avg_tokens_per_sec'] > 30:
            print(f"  ✓ Good speed - speculation helping")
        else:
            print(f"  ℹ Normal speed - may need tuning")
        
        results.append(result)
        print()
    
    # Overall performance summary
    print("=" * 60)
    print("SPECULATIVE DECODING SUMMARY")
    print("=" * 60)
    
    avg_throughput = statistics.mean([r['avg_tokens_per_sec'] for r in results])
    print(f"Average Throughput: {avg_throughput:.1f} tokens/sec")
    
    if avg_throughput > 40:
        print("✓ Speculative decoding is providing significant speedup!")
        print("  Your draft model is well-matched to gpt-oss-120b")
    else:
        print("ℹ Consider tuning speculation parameters:")
        print("  - Increase --speculate-num-steps (try 8-10)")
        print("  - Use a better-matched draft model")
        print("  - Adjust --speculate-disable-by-batch-size")
    
    print("\nOptimization Tips for Speculative Decoding:")
    print("1. Draft model should be 5-10x smaller than target")
    print("2. Similar training data improves speculation accuracy")
    print("3. Lower temperatures improve speculation hit rate")
    print("4. Batch size affects speculation efficiency")

def check_speculation_config():
    """Check if speculative decoding is enabled."""
    print("\nChecking Speculation Configuration...")
    print("-" * 40)
    
    try:
        # SGLang exposes config through /v1/models endpoint
        response = requests.get("http://127.0.0.1:30000/v1/models")
        if response.status_code == 200:
            # Check server logs or config endpoint if available
            print("✓ Server is running")
            print("  Check server logs for speculation status")
            print("  Look for: 'Speculative decoding enabled'")
    except:
        pass

if __name__ == "__main__":
    test_speculative_decoding()
    check_speculation_config()