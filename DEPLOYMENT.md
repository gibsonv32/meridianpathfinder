# MERIDIAN Deployment Guide - Local/DGX Single-User

## Quick Start

For single-user local or DGX deployment, the system is ready to use with minimal setup:

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 2. Run deployment script
./deploy-local.sh

# 3. Start API server
meridian api start
# Or with custom settings:
meridian api start --host 127.0.0.1 --port 8000 --workers 2 --timeout 600
```

## What's Been Hardened

### Security & Reliability
- ✅ Default to localhost (127.0.0.1) instead of 0.0.0.0
- ✅ Environment variable configuration support
- ✅ Request logging and monitoring
- ✅ Graceful shutdown handling (SIGTERM/SIGINT)
- ✅ Configurable CORS origins
- ✅ Resource limits and timeouts

### Configuration (.env)
```bash
# Core settings
API_HOST=127.0.0.1  # Localhost only by default
API_PORT=8000
LOG_LEVEL=INFO

# LLM Configuration
ANTHROPIC_API_KEY=your-key-here

# Resource limits
REQUEST_TIMEOUT=300
MAX_CONCURRENT_MODES=1
```

## Running as a Service (Optional)

For always-on deployment on DGX or workstation:

```bash
# Install systemd service
sudo cp meridian.service /etc/systemd/system/meridian@$USER.service
sudo systemctl daemon-reload
sudo systemctl enable meridian@$USER
sudo systemctl start meridian@$USER

# Check status
systemctl status meridian@$USER

# View logs
journalctl -u meridian@$USER -f
```

## API Endpoints

Access the API documentation at: http://localhost:8000/docs

Key endpoints:
- `GET /` - Health check
- `POST /project/init` - Initialize project
- `GET /project/status` - Get project status
- `POST /mode/run` - Execute a mode
- `GET /artifacts/list` - List artifacts
- `POST /demo` - Run demo pipeline

## Monitoring

View logs in real-time:
```bash
# If running directly
meridian api start 2>&1 | tee meridian.log

# If running as service
journalctl -u meridian@$USER -f
```

## Resource Management

The deployment is configured with sensible defaults:
- Single worker process (increase with `--workers` for more throughput)
- 300s request timeout (adjust with `--timeout`)
- Logging to stdout/stderr (captured by systemd if using service)

## Troubleshooting

1. **Port already in use**: Change port in .env or use `--port` flag
2. **Permission denied**: Ensure user has write access to data/ and .meridian/
3. **API key errors**: Check .env file has correct ANTHROPIC_API_KEY
4. **Out of memory**: Reduce concurrent modes in .env

## For Production Cloud Deployment

If you need multi-user cloud deployment later, see PRODUCTION_CHECKLIST.md for:
- Database backend (PostgreSQL)
- Authentication (JWT/OAuth2)
- Container orchestration (Kubernetes)
- Advanced monitoring (Prometheus/Grafana)

The current setup is perfectly suitable for:
- Single-user research workstations
- DGX development environments
- Local testing and development
- Private network deployments