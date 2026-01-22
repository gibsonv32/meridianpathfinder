#!/bin/bash
# Start SGLang server for gpt-oss-120b

echo "Starting SGLang Server for gpt-oss-120b"
echo "========================================"

# SGLang specific configuration
MODEL_PATH="/mnt/spark-data3/models/gpt-oss-120b"
PORT=30000

# Start SGLang server with SEL runtime
python -m sglang.launch_server \
    --model-path $MODEL_PATH \
    --tokenizer-path $MODEL_PATH \
    --host 0.0.0.0 \
    --port $PORT \
    --dp 1 \
    --tp 1 \
    --trust-remote-code \
    --context-length 32768 \
    --mem-fraction-static 0.85 \
    --schedule-policy lpm \
    --enable-flashinfer

# Alternative minimal start command:
# python -m sglang.launch_server --model-path $MODEL_PATH --port $PORT