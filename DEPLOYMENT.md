# MERIDIAN Deployment Guide - Self-Hosted (Secure by Default)

## Security Posture

Services bind to **localhost only** on the DGX. Access from your MacBook via **SSH tunnel**.

This protects against:
- ❌ Accidental LAN exposure
- ❌ Fat-finger port forwarding mistakes
- ❌ DHCP IP changes breaking bookmarks

---

## Quick Start

### 1. First-time setup on DGX

```bash
ssh gibsonv32@spark-ad77
cd /home/gibsonv32/dev/meridian

# Create and secure .env
cp .env.example .env
chmod 600 .env
nano .env  # Add your ANTHROPIC_API_KEY
```

### 2. Deploy from MacBook

```bash
cd /path/to/meridianpathfinder/try

# Full deploy (sync + start)
./deploy/deploy-to-spark.sh

# Or step by step:
./deploy/deploy-to-spark.sh --sync    # Sync code
./deploy/deploy-to-spark.sh --start   # Start services
./deploy/deploy-to-spark.sh --status  # Check status
```

### 3. Access via SSH tunnel

```bash
# Open tunnel (runs in foreground)
./deploy/deploy-to-spark.sh --tunnel

# Or manually:
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 gibsonv32@spark-ad77
```

Then open in browser:
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## Deploy Script Commands

| Command | Description |
|---------|-------------|
| `./deploy/deploy-to-spark.sh` | Full deploy (sync + start + status) |
| `--sync`, `-s` | Sync code to DGX only |
| `--start` | Start Docker services |
| `--stop` | Stop Docker services |
| `--status` | Check container status & security |
| `--health`, `-H` | Detailed health check of all endpoints |
| `--logs`, `-l` | Tail container logs |
| `--tunnel`, `-t` | Open SSH tunnel for browser access |

---

## Self-Hosted Hardening Checklist

- [x] Services bind to localhost (`127.0.0.1:port` in docker-compose)
- [x] Access via SSH tunnels from MacBook
- [x] `.env` stays local on DGX, never synced back (`chmod 600`)
- [x] Docker containers auto-restart (`restart: unless-stopped`)
- [x] Health/logs/status commands in deploy script

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  DGX Spark (spark-ad77)                     │
│              All services bound to 127.0.0.1                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐       ┌─────────────────────────────┐ │
│  │ SGLang Container│       │     Meridian API            │ │
│  │ gpt-oss-120b    │◄──────│     127.0.0.1:8000          │ │
│  │ 127.0.0.1:30000 │       └─────────────────────────────┘ │
│  └─────────────────┘                 │                      │
│                                      │ Mode 5 only          │
│                                      ▼                      │
│                            ┌─────────────────┐             │
│                            │ Anthropic API   │             │
│                            │ Claude Opus 4.5 │             │
│                            └─────────────────┘             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Dashboard: 127.0.0.1:3000                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │ SSH Tunnel
                           │ -L 3000:localhost:3000
                           │ -L 8000:localhost:8000
                           ▼
                 ┌─────────────────┐
                 │    MacBook      │
                 │  localhost:3000 │
                 │  localhost:8000 │
                 └─────────────────┘
```

---

## LLM Configuration

| Task | Model | Endpoint |
|------|-------|----------|
| **Reasoning** (Modes 0-4, 6-7) | gpt-oss-120b | SGLang @ localhost:30000 |
| **Code Generation** (Mode 5) | Claude Opus 4.5 | Anthropic API |

---

## Troubleshooting

```bash
# Check if services are running
./deploy/deploy-to-spark.sh --status

# Detailed health check
./deploy/deploy-to-spark.sh --health

# View logs
./deploy/deploy-to-spark.sh --logs

# Restart services
./deploy/deploy-to-spark.sh --stop
./deploy/deploy-to-spark.sh --start
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Can't connect to localhost:3000 | Open SSH tunnel first: `./deploy/deploy-to-spark.sh --tunnel` |
| SGLang not running | `docker start sglang-gpt-oss` on DGX |
| .env not found | Copy from .env.example and configure |
| Permission denied on .env | `chmod 600 .env` |

---

## Running as Systemd Service (Optional)

For always-on deployment:

```bash
# On DGX
sudo cp meridian.service /etc/systemd/system/meridian@$USER.service
sudo systemctl daemon-reload
sudo systemctl enable meridian@$USER
sudo systemctl start meridian@$USER

# Check status
systemctl status meridian@$USER
journalctl -u meridian@$USER -f
```