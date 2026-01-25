#!/bin/bash
# Start SGLang server with Speculative Decoding for gpt-oss-120b
# This uses a smaller draft model to accelerate generation

echo "Starting SGLang with Speculative Decoding"
echo "=========================================="

# Main model (target)
TARGET_MODEL="/mnt/spark-data3/models/gpt-oss-120b"

# Draft model for speculation (smaller, faster model)
# Common choices: Qwen2-7B, Llama-7B, or any smaller version
DRAFT_MODEL="/mnt/spark-data3/models/Qwen2-7B"  # Adjust to your draft model

# Server configuration
PORT=30000
HOST="0.0.0.0"

# Start SGLang with speculative decoding
python -m sglang.launch_server \
    --model-path $TARGET_MODEL \
    --port $PORT \
    --host $HOST \
    --tp 1 \
    --speculate-model $DRAFT_MODEL \
    --speculate-num-steps 5 \
    --speculate-disable-by-batch-size 4 \
    --max-batch-size 256 \
    --schedule-policy lpm \
    --enable-flashinfer \
    --mem-fraction-static 0.85 \
    --context-length 32768 \
    --trust-remote-code

# Alternative with more aggressive speculation
# python -m sglang.launch_server \
#     --model-path $TARGET_MODEL \
#     --port $PORT \
#     --speculate-model $DRAFT_MODEL \
#     --speculate-num-steps 8 \
#     --speculate-disable-by-batch-size 2 \
#     --enable-speculative \
#     --enable-flashinfer