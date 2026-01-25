# MERIDIAN LLM Provider Configuration Guide

MERIDIAN uses Large Language Models (LLMs) to generate intelligent narratives, insights, and recommendations throughout the ML pipeline. This guide covers configuration for supported providers.

## Supported Providers

- **Anthropic Claude** - Cloud-based, high-quality models
- **Ollama** - Local, open-source models

## Provider Configuration

### Anthropic Claude

#### Setup

1. **Get an API Key**:
   - Sign up at [console.anthropic.com](https://console.anthropic.com)
   - Navigate to API Keys section
   - Create a new key

2. **Configure Environment**:
   ```bash
   # Add to your shell profile (.bashrc, .zshrc, etc.)
   export ANTHROPIC_API_KEY="sk-ant-api03-..."
   
   # Or use a .env file
   echo "ANTHROPIC_API_KEY=sk-ant-api03-..." >> .env
   ```

3. **Configure MERIDIAN**:
   ```bash
   # Set provider
   meridian llm set-provider anthropic
   
   # Set model (recommended)
   meridian llm set-model claude-3-haiku-20240307
   
   # Test connection
   meridian llm test
   ```

#### Available Models

| Model | Speed | Quality | Cost | Use Case |
|-------|--------|---------|------|----------|
| `claude-3-haiku-20240307` | Fast | Good | Low | Default, most operations |
| `claude-3-sonnet-20240229` | Medium | Better | Medium | Complex analysis |
| `claude-3-opus-20240229` | Slower | Best | High | Critical decisions |

#### Configuration in meridian.yaml

```yaml
llm:
  provider: anthropic
  model: claude-3-haiku-20240307
  temperature: 0.3  # Lower = more deterministic
  max_tokens: 4096  # Maximum response length
  timeout: 30  # Request timeout in seconds
```

#### Troubleshooting Anthropic

**Connection Failed:**
```bash
# Check API key is set
echo $ANTHROPIC_API_KEY

# Verify key format (should start with sk-ant-)
meridian llm status

# Test with curl
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
```

**Rate Limits:**
- Haiku: 50 requests/minute
- Sonnet: 40 requests/minute  
- Opus: 30 requests/minute

### Ollama (Local Models)

#### Setup

1. **Install Ollama**:
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Windows
   # Download from https://ollama.ai/download
   ```

2. **Start Ollama Service**:
   ```bash
   # Start server
   ollama serve
   
   # Verify it's running
   curl http://localhost:11434/api/tags
   ```

3. **Pull Models**:
   ```bash
   # Recommended models
   ollama pull llama2:7b          # Good balance
   ollama pull mistral:7b         # Fast, efficient
   ollama pull codellama:13b      # Code-focused
   ollama pull mixtral:8x7b       # High quality
   
   # List available models
   ollama list
   ```

4. **Configure MERIDIAN**:
   ```bash
   # Set provider
   meridian llm set-provider ollama
   
   # Set model
   meridian llm set-model llama2:7b
   
   # Test connection
   meridian llm test
   ```

#### Configuration in meridian.yaml

```yaml
llm:
  provider: ollama
  model: llama2:7b
  base_url: http://localhost:11434  # Ollama server URL
  temperature: 0.3
  max_tokens: 4096
  timeout: 60  # Longer timeout for local models
```

#### Available Local Models

| Model | Size | Speed | Quality | RAM Required |
|-------|------|-------|---------|--------------|
| `llama2:7b` | 7B | Fast | Good | 8GB |
| `mistral:7b` | 7B | Fast | Good | 8GB |
| `codellama:13b` | 13B | Medium | Better for code | 16GB |
| `mixtral:8x7b` | 47B | Slow | Excellent | 48GB |
| `llama2:70b` | 70B | Very Slow | Best | 64GB |

#### Performance Tuning

```yaml
llm:
  provider: ollama
  model: llama2:7b
  options:
    num_thread: 8  # CPU threads
    num_gpu: 1     # GPUs to use
    num_ctx: 4096  # Context window
    temperature: 0.3
    top_p: 0.9
    repeat_penalty: 1.1
```

#### Troubleshooting Ollama

**Connection Refused:**
```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve

# Check port is accessible
netstat -an | grep 11434
```

**Model Not Found:**
```bash
# List available models
ollama list

# Pull missing model
ollama pull llama2:7b
```

**Out of Memory:**
```bash
# Use smaller model
ollama pull llama2:7b  # Instead of 13b/70b

# Adjust context size in meridian.yaml
llm:
  options:
    num_ctx: 2048  # Reduce from 4096
```

## Advanced Configuration

### Multi-Provider Setup

Use different providers for different modes:

```yaml
# meridian.yaml
llm:
  default:
    provider: ollama
    model: llama2:7b
  
  # Override for specific modes
  mode_overrides:
    mode_4:  # Business Case needs higher quality
      provider: anthropic
      model: claude-3-sonnet-20240229
    mode_6_5:  # Interpretation needs best quality
      provider: anthropic
      model: claude-3-opus-20240229
```

### Fallback Configuration

Configure fallback providers:

```yaml
llm:
  primary:
    provider: anthropic
    model: claude-3-haiku-20240307
  
  fallback:
    provider: ollama
    model: llama2:7b
  
  retry_policy:
    max_attempts: 3
    backoff_seconds: 5
```

### Custom Endpoints

For enterprise or custom deployments:

```yaml
llm:
  provider: anthropic
  base_url: https://your-proxy.company.com/anthropic
  headers:
    X-Custom-Header: value
  
  # Or for Ollama remote server
  provider: ollama
  base_url: http://gpu-server.local:11434
```

## Security Best Practices

### API Key Management

**DON'T:**
- Hardcode keys in code
- Commit keys to git
- Share keys in documentation

**DO:**
```bash
# Use environment variables
export ANTHROPIC_API_KEY="..."

# Use secure key storage
# macOS
security add-generic-password -s "MERIDIAN" -a "ANTHROPIC_API_KEY" -w "sk-ant-..."
export ANTHROPIC_API_KEY=$(security find-generic-password -s "MERIDIAN" -a "ANTHROPIC_API_KEY" -w)

# Linux (using pass)
pass insert meridian/anthropic_key
export ANTHROPIC_API_KEY=$(pass show meridian/anthropic_key)

# Use .env files (git-ignored)
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
echo ".env" >> .gitignore
```

### Network Security

For production environments:

```yaml
llm:
  provider: anthropic
  proxy: http://corporate-proxy:8080
  verify_ssl: true
  timeout: 30
  max_retries: 3
```

## Cost Management

### Anthropic Pricing (as of 2024)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Haiku | $0.25 | $1.25 |
| Sonnet | $3.00 | $15.00 |
| Opus | $15.00 | $75.00 |

### Cost Optimization Strategies

1. **Use Appropriate Models**:
   ```yaml
   # Use Haiku for most operations
   llm:
     model: claude-3-haiku-20240307
   ```

2. **Limit Token Usage**:
   ```yaml
   llm:
     max_tokens: 2048  # Reduce from 4096
     temperature: 0.1  # More focused responses
   ```

3. **Enable Caching**:
   ```yaml
   llm:
     cache_enabled: true
     cache_ttl_seconds: 3600
   ```

4. **Use Headless Mode for Development**:
   ```bash
   # Skip LLM calls during testing
   meridian mode 2 run --data data.csv --target target --headless
   ```

## Monitoring & Logging

### Enable Detailed Logging

```yaml
llm:
  logging:
    enabled: true
    level: DEBUG
    log_file: .meridian/llm.log
    log_requests: true  # Log full requests
    log_responses: false  # Don't log responses (may contain sensitive data)
```

### Usage Tracking

```bash
# View LLM usage statistics
meridian llm usage

# Export usage for analysis
meridian llm usage --export usage_report.json
```

## Testing LLM Integration

### Basic Test

```bash
# Test connection and model
meridian llm test

# Expected output:
# provider: anthropic
# model: claude-3-haiku-20240307
# connection: ok
```

### Integration Test

```bash
# Run a simple mode with LLM
meridian mode 0 run --data data/sample.csv

# Verify narrative generation
meridian artifacts show --type Mode0GatePacket | jq '.narrative'
```

### Benchmark Different Models

```bash
#!/bin/bash
# Compare model performance

for model in "llama2:7b" "mistral:7b" "mixtral:8x7b"; do
    echo "Testing $model..."
    meridian llm set-model $model
    time meridian mode 2 run --data data.csv --target target
    echo "---"
done
```

## Troubleshooting Guide

### Common Issues

| Issue | Solution |
|-------|----------|
| "API key not found" | Check environment variable: `echo $ANTHROPIC_API_KEY` |
| "Connection refused" | Start Ollama: `ollama serve` |
| "Model not found" | Pull model: `ollama pull llama2:7b` |
| "Rate limit exceeded" | Wait 60s or switch to different model |
| "Timeout error" | Increase timeout in meridian.yaml |
| "Out of memory" | Use smaller model or reduce context size |

### Debug Mode

Enable verbose logging:

```bash
# Set debug environment
export MERIDIAN_DEBUG=true
export MERIDIAN_LLM_DEBUG=true

# Run with verbose output
meridian --verbose mode 2 run --data data.csv --target target
```

### Health Check Script

```python
#!/usr/bin/env python
"""Check LLM provider health"""

import os
import requests
from meridian.llm.providers import get_provider
from meridian.config import load_config

def check_health():
    config = load_config()
    provider = get_provider(config)
    
    print(f"Provider: {config['llm']['provider']}")
    print(f"Model: {provider.model_name}")
    
    # Test connection
    if provider.test_connection():
        print("✓ Connection successful")
    else:
        print("✗ Connection failed")
        return False
    
    # Test generation
    try:
        response = provider.generate("Say 'test successful'", max_tokens=10)
        print(f"✓ Generation test: {response[:50]}")
        return True
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        return False

if __name__ == "__main__":
    check_health()
```

## FAQ

**Q: Can I use both providers?**
A: Yes, configure primary and fallback providers in meridian.yaml.

**Q: Which provider is faster?**
A: Ollama (local) has no network latency but depends on your hardware. Claude Haiku is fastest for cloud.

**Q: Can I use custom/fine-tuned models?**
A: Yes with Ollama. Pull or create custom models using Ollama's Modelfile.

**Q: How do I reduce costs?**
A: Use Haiku model, enable caching, reduce max_tokens, use --headless for development.

**Q: Can I use OpenAI GPT models?**
A: Not currently supported, but you can add a custom provider by extending the LLMProvider class.

## Support

- Anthropic Support: [support.anthropic.com](https://support.anthropic.com)
- Ollama Documentation: [ollama.ai/docs](https://ollama.ai/docs)
- MERIDIAN Issues: [github.com/yourusername/meridianpathfinder/issues](https://github.com/yourusername/meridianpathfinder/issues)