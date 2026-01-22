# MERIDIAN Robustness Features

This document describes the robustness improvements added to MERIDIAN for reliable single-user operation.

## 1. Structured Logging

### Configuration
```python
from meridian.logging_config import setup_logging, get_logger

# Setup logging with custom level and file
logger = setup_logging(level="DEBUG", log_file=Path("custom.log"))

# Get logger for module
logger = get_logger("meridian.my_module")
```

### Features
- Automatic log rotation (10MB max, 5 backups)
- Structured context (mode, operation, artifact_id)
- Logs saved to `~/.meridian/logs/meridian.log`
- Console and file output

### Usage Example
```python
from meridian.logging_config import log_operation

with log_operation("data_processing", mode="2", artifact_id="abc-123"):
    # Your code here - automatically logs start/success/failure
    process_data()
```

## 2. Retry Logic with Exponential Backoff

### Basic Retry Decorator
```python
from meridian.utils.retry import exponential_backoff

@exponential_backoff(max_retries=5, initial_delay=2)
def call_llm_api(prompt):
    # This will automatically retry on failure
    return llm.generate(prompt)
```

### Retry with Fallback
```python
from meridian.utils.retry import retry_with_fallback

result = retry_with_fallback(
    primary_func=lambda: call_claude_api(prompt),
    fallback_func=lambda: call_local_llm(prompt),
    max_retries=3
)
```

### Features
- Exponential backoff with jitter
- Configurable retry counts and delays
- Fallback to alternative functions
- Detailed retry logging

## 3. Enhanced Exception Handling

### Contextual Exceptions
```python
from meridian.utils.exceptions import ErrorContext, MeridianError

with ErrorContext("processing_data", mode="2", data_path=str(path)):
    df = pd.read_csv(path)
    # If error occurs, it will include all context
```

### Custom Exception Types
- `MeridianError` - Base exception with context
- `DataError` - Data validation failures
- `GateError` - Gate condition violations
- `ArtifactError` - Artifact operation failures
- `LLMError` - LLM API failures
- `FileOperationError` - File I/O failures

### Input Validation
```python
from meridian.utils.exceptions import validate_input

data_path = validate_input(
    data_path, Path, "data_path", "load_data", mode="2"
)
```

## 4. Atomic File Operations

### Atomic Write
```python
from meridian.utils.file_ops import atomic_write, atomic_write_json

# Text file
atomic_write("config.txt", "content", create_backup=True)

# JSON file
atomic_write_json("artifact.json", {"data": "value"})
```

### Safe Read
```python
from meridian.utils.file_ops import safe_read, safe_read_json

# Returns default if file doesn't exist or fails
config = safe_read_json("config.json", default={})
```

### Context Manager
```python
from meridian.utils.file_ops import AtomicFileWriter

with AtomicFileWriter("data.json") as f:
    json.dump(data, f)
    # File is written atomically on success
    # Cleaned up on failure
```

### Features
- Write to temp file, then atomic rename
- Automatic backups (.backup files)
- Safe reads with defaults
- Proper permission preservation

## 5. Backup System

### CLI Commands
```bash
# Create backup
meridian backup create --name "before-upgrade"

# Include data directory
meridian backup create --include-data

# List backups
meridian backup list

# Restore backup
meridian backup restore backup-file.tar.gz --target /new/location

# Clean old backups (keep 5 most recent)
meridian backup cleanup --keep 5
```

### Programmatic Usage
```python
from meridian.utils.backup import MeridianBackup

backup_mgr = MeridianBackup(project_path)

# Create backup
backup_file = backup_mgr.create_backup(
    name="my-backup",
    include_data=True,
    compress=True
)

# Restore backup
backup_mgr.restore_backup(backup_file, target_path="/new/location")
```

### Features
- Compressed tar.gz archives
- Metadata tracking (JSON sidecar files)
- Selective data inclusion
- Automatic cleanup of old backups
- Default location: `~/.meridian/backups/`

## Usage in Practice

### LLM Calls with Retry
```python
from meridian.utils.retry import exponential_backoff
from meridian.logging_config import get_logger

logger = get_logger("meridian.llm")

@exponential_backoff(
    max_retries=5,
    initial_delay=2,
    max_delay=60,
    retriable_exceptions=(APIError, TimeoutError)
)
def generate_narrative(prompt):
    logger.info("Generating narrative", extra={"prompt_length": len(prompt)})
    return llm_provider.generate(prompt)
```

### Artifact Writing with Atomicity
```python
from meridian.utils.file_ops import atomic_write_json
from meridian.utils.exceptions import ErrorContext

def save_artifact(artifact_data, artifact_path):
    with ErrorContext("save_artifact", artifact_id=artifact_data["id"]):
        # This will:
        # 1. Create backup of existing file
        # 2. Write to temp file
        # 3. Atomically rename on success
        # 4. Clean up on failure
        atomic_write_json(artifact_path, artifact_data)
```

### Complete Example
```python
from meridian.logging_config import log_operation
from meridian.utils.retry import exponential_backoff
from meridian.utils.file_ops import atomic_write_json
from meridian.utils.exceptions import ErrorContext, validate_input

@exponential_backoff(max_retries=3)
def process_mode_2(data_path, target_col):
    # Validate inputs
    data_path = validate_input(data_path, Path, "data_path", "mode_2", mode="2")
    target_col = validate_input(target_col, str, "target_col", "mode_2", mode="2")
    
    with log_operation("mode_2_execution", mode="2"):
        with ErrorContext("load_data", mode="2", data_path=str(data_path)):
            df = pd.read_csv(data_path)
        
        # Process data...
        result = {"analysis": "complete"}
        
        # Save atomically
        artifact_path = Path(".meridian/artifacts/mode_2/result.json")
        atomic_write_json(artifact_path, result)
        
        return result
```

## Configuration

### Environment Variables
```bash
# Logging level
export MERIDIAN_LOG_LEVEL=DEBUG

# Log file location
export MERIDIAN_LOG_FILE=/var/log/meridian.log

# Backup directory
export MERIDIAN_BACKUP_DIR=/backups/meridian
```

### Python Configuration
```python
# At application startup
from meridian.logging_config import setup_logging

# Configure logging once
setup_logging(
    level="INFO",
    log_file=Path("/var/log/meridian.log"),
    console=True
)
```

## Best Practices

1. **Always use atomic writes for critical files** (artifacts, state, config)
2. **Wrap LLM calls with retry logic** to handle transient failures
3. **Use context managers** for operations that need cleanup
4. **Create backups before major operations** or mode transitions
5. **Log with context** (mode, operation, artifact_id) for debugging
6. **Validate inputs early** with descriptive error messages
7. **Set up daily backup cleanup** to manage disk space

## Monitoring

Check logs for issues:
```bash
# View recent errors
grep ERROR ~/.meridian/logs/meridian.log | tail -20

# View retry attempts
grep "retry" ~/.meridian/logs/meridian.log

# Check backup status
ls -lah ~/.meridian/backups/
```

## Recovery

If something goes wrong:
```bash
# 1. Check logs
tail -100 ~/.meridian/logs/meridian.log

# 2. Restore from backup
meridian backup list
meridian backup restore <backup-file>

# 3. Check for .backup files
find .meridian -name "*.backup" -mtime -1

# 4. Verify artifacts
meridian artifacts list --verify
```