# MERIDIAN with SGLang Speculative Decoding Configuration

## What is Speculative Decoding?
Speculative decoding uses a smaller "draft" model to predict multiple tokens ahead, then validates them with the large model in parallel. This can provide 2-5x speedup without changing output quality.

## Architecture for gpt-oss-120b
```
┌─────────────────┐
│  Draft Model    │ ← Fast predictions (e.g., Qwen-7B)
│   (7-14B)       │   Generates 5-8 tokens ahead
└────────┬────────┘
         │ Speculative tokens
         ▼
┌─────────────────┐
│  gpt-oss-120b   │ ← Validates in parallel
│  Target Model   │   Accepts/rejects speculations
└────────┬────────┘
         │
         ▼
    Final Output
```

## Optimal Configuration for MERIDIAN

### 1. Model Selection
```yaml
# meridian.yaml
llm:
  provider: openai
  base_url: http://127.0.0.1:30000/v1
  model: gpt-oss-120b  # SGLang will handle this
  
  # Speculation works best with lower temperature
  temperature: 0.3  # Lower = better speculation accuracy
  
  # Mode-specific optimizations
  mode_overrides:
    mode_0:  # Planning - highly predictable
      temperature: 0.1  # Very high speculation hit rate
    mode_5:  # Code generation - predictable patterns
      temperature: 0.2  # Good speculation
    mode_7:  # Creative - less predictable
      temperature: 0.7  # Lower speculation benefit
```

### 2. SGLang Server Launch
```bash
# Optimal for gpt-oss-120b with speculation
python -m sglang.launch_server \
    --model-path /path/to/gpt-oss-120b \
    --port 30000 \
    --tp 2 \
    --speculate-model /path/to/qwen-7b \
    --speculate-num-steps 6 \
    --speculate-disable-by-batch-size 4 \
    --schedule-policy lpm \
    --enable-flashinfer \
    --mem-fraction-static 0.85
```

### 3. Performance Expectations

| Workload | Without Speculation | With Speculation | Speedup |
|----------|-------------------|------------------|---------|
| Code Generation | 30 tok/s | 90-120 tok/s | 3-4x |
| Factual Q&A | 25 tok/s | 75-100 tok/s | 3-4x |
| Planning | 35 tok/s | 140-175 tok/s | 4-5x |
| Creative Writing | 30 tok/s | 45-60 tok/s | 1.5-2x |

## Deployment on Spark/DGX

### Production Script
```bash
#!/bin/bash
# /mnt/spark-data3/start_meridian_sglang.sh

# GPU allocation
export CUDA_VISIBLE_DEVICES=0,1  # Use 2 GPUs

# Models
TARGET="/mnt/models/gpt-oss-120b"
DRAFT="/mnt/models/qwen2-7b"  # Or your draft model

# Start SGLang with speculation
python -m sglang.launch_server \
    --model-path $TARGET \
    --speculate-model $DRAFT \
    --port 30000 \
    --tp 2 \
    --speculate-num-steps 6 \
    --max-batch-size 256 \
    --enable-flashinfer \
    --schedule-policy lpm \
    --trust-remote-code \
    > /var/log/sglang.log 2>&1 &
```

## Testing Speculative Performance
```bash
# Run performance test
python3 test_speculative_performance.py

# Monitor speculation hit rate in logs
tail -f /var/log/sglang.log | grep "speculation"
```

## Optimization Tips

1. **Draft Model Selection**
   - Should be 8-15x smaller than target
   - Same architecture family improves accuracy
   - Fine-tuned on similar data is best

2. **Tuning Parameters**
   - `--speculate-num-steps`: Start with 5, increase to 8 for predictable tasks
   - `--speculate-disable-by-batch-size`: Lower for better latency
   - Temperature: Keep < 0.5 for best speculation

3. **MERIDIAN Mode Optimization**
   - Modes 0-4: Low temperature (0.1-0.3) - high speculation benefit
   - Mode 5 (code): Temperature 0.2 - excellent speculation
   - Modes 6-7: Higher temperature - less benefit

## Monitoring
```python
# Add to your MERIDIAN code to track performance
import time

start = time.time()
response = provider.complete(prompt)
latency = time.time() - start
tokens = len(response.split())
print(f"Tokens/sec: {tokens/latency:.1f}")
```