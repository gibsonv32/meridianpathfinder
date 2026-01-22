"""Atomic file operations for MERIDIAN"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union
import hashlib

from meridian.logging_config import get_logger
from meridian.utils.exceptions import FileOperationError, ErrorContext

logger = get_logger("meridian.file_ops")


def atomic_write(
    file_path: Union[str, Path],
    content: Union[str, bytes],
    mode: str = "w",
    encoding: Optional[str] = "utf-8",
    create_backup: bool = True
) -> Path:
    """
    Write file atomically (write to temp, then rename).
    
    Args:
        file_path: Target file path
        content: Content to write
        mode: File mode ('w' for text, 'wb' for binary)
        encoding: Text encoding (ignored for binary mode)
        create_backup: Whether to backup existing file
        
    Returns:
        Path to written file
        
    Raises:
        FileOperationError: If write fails
        
    Example:
        atomic_write("config.json", json.dumps(data), create_backup=True)
    """
    file_path = Path(file_path)
    
    with ErrorContext("atomic_write", file_path=str(file_path)):
        # Create parent directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup existing file if requested
        if create_backup and file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + ".backup")
            logger.debug(f"Creating backup: {backup_path}")
            shutil.copy2(file_path, backup_path)
        
        # Write to temporary file in same directory (for same filesystem)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=f".{file_path.stem}_",
            suffix=".tmp"
        )
        
        try:
            # Write content
            if mode == "wb":
                os.write(temp_fd, content if isinstance(content, bytes) else content.encode())
            else:
                os.write(temp_fd, content.encode(encoding) if isinstance(content, str) else content)
            
            os.close(temp_fd)
            
            # Set proper permissions (match original if exists)
            if file_path.exists():
                shutil.copystat(file_path, temp_path)
            else:
                os.chmod(temp_path, 0o644)
            
            # Atomic rename (overwrites existing)
            os.replace(temp_path, file_path)
            
            logger.info(
                f"Atomic write completed: {file_path}",
                extra={
                    "operation": "atomic_write",
                    "file_path": str(file_path),
                    "size": len(content) if isinstance(content, (str, bytes)) else 0
                }
            )
            
            return file_path
            
        except Exception as e:
            # Clean up temp file on error
            try:
                os.close(temp_fd)
            except:
                pass
            
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            raise FileOperationError(
                f"Failed to write file atomically",
                file_path=file_path,
                operation_type="write",
                cause=e
            )


def atomic_write_json(
    file_path: Union[str, Path],
    data: Any,
    indent: int = 2,
    create_backup: bool = True
) -> Path:
    """
    Write JSON data atomically.
    
    Args:
        file_path: Target file path
        data: Data to serialize to JSON
        indent: JSON indentation
        create_backup: Whether to backup existing file
        
    Returns:
        Path to written file
        
    Example:
        atomic_write_json("artifact.json", {"data": "value"})
    """
    content = json.dumps(data, indent=indent, default=str)
    return atomic_write(file_path, content, mode="w", create_backup=create_backup)


def safe_read(
    file_path: Union[str, Path],
    mode: str = "r",
    encoding: Optional[str] = "utf-8",
    default: Any = None
) -> Union[str, bytes, Any]:
    """
    Read file safely with error handling.
    
    Args:
        file_path: File to read
        mode: Read mode ('r' for text, 'rb' for binary)
        encoding: Text encoding
        default: Default value if file doesn't exist
        
    Returns:
        File content or default value
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.debug(f"File not found, returning default: {file_path}")
        return default
    
    with ErrorContext("safe_read", file_path=str(file_path)):
        try:
            if mode == "rb":
                return file_path.read_bytes()
            else:
                return file_path.read_text(encoding=encoding)
        except Exception as e:
            logger.warning(f"Failed to read file, returning default: {e}")
            return default


def safe_read_json(
    file_path: Union[str, Path],
    default: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Read JSON file safely.
    
    Args:
        file_path: JSON file to read
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        Parsed JSON data or default
    """
    if default is None:
        default = {}
    
    content = safe_read(file_path, default=None)
    if content is None:
        return default
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in {file_path}: {e}")
        return default


def compute_file_hash(file_path: Union[str, Path]) -> str:
    """
    Compute SHA256 hash of file content.
    
    Args:
        file_path: File to hash
        
    Returns:
        Hex digest of SHA256 hash
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileOperationError(
            f"File not found for hashing",
            file_path=file_path,
            operation_type="hash"
        )
    
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if needed.
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    path = Path(path)
    
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        raise FileOperationError(
            f"Failed to create directory",
            file_path=path,
            operation_type="mkdir",
            cause=e
        )


def safe_move(
    source: Union[str, Path],
    destination: Union[str, Path],
    create_backup: bool = True
) -> Path:
    """
    Safely move file with optional backup.
    
    Args:
        source: Source file path
        destination: Destination file path
        create_backup: Backup destination if it exists
        
    Returns:
        Destination path
    """
    source = Path(source)
    destination = Path(destination)
    
    with ErrorContext("safe_move", source=str(source), destination=str(destination)):
        if not source.exists():
            raise FileOperationError(
                f"Source file not found",
                file_path=source,
                operation_type="move"
            )
        
        # Backup destination if it exists
        if create_backup and destination.exists():
            backup_path = destination.with_suffix(destination.suffix + ".backup")
            logger.debug(f"Backing up destination: {backup_path}")
            shutil.copy2(destination, backup_path)
        
        # Ensure destination directory exists
        ensure_directory(destination.parent)
        
        # Move file
        shutil.move(str(source), str(destination))
        
        logger.info(f"File moved: {source} -> {destination}")
        return destination


def safe_delete(
    file_path: Union[str, Path],
    create_backup: bool = True
) -> bool:
    """
    Safely delete file with optional backup.
    
    Args:
        file_path: File to delete
        create_backup: Create backup before deletion
        
    Returns:
        True if deleted, False if didn't exist
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return False
    
    with ErrorContext("safe_delete", file_path=str(file_path)):
        # Create backup if requested
        if create_backup:
            backup_path = file_path.with_suffix(file_path.suffix + ".deleted")
            logger.debug(f"Creating deletion backup: {backup_path}")
            shutil.copy2(file_path, backup_path)
        
        # Delete file
        file_path.unlink()
        logger.info(f"File deleted: {file_path}")
        return True


class AtomicFileWriter:
    """
    Context manager for atomic file writing.
    
    Example:
        with AtomicFileWriter("data.json") as f:
            json.dump(data, f)
    """
    
    def __init__(
        self,
        file_path: Union[str, Path],
        mode: str = "w",
        encoding: Optional[str] = "utf-8",
        create_backup: bool = True
    ):
        self.file_path = Path(file_path)
        self.mode = mode
        self.encoding = encoding
        self.create_backup = create_backup
        self.temp_file = None
        self.temp_path = None
        
    def __enter__(self):
        # Create parent directory
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if needed
        if self.create_backup and self.file_path.exists():
            backup_path = self.file_path.with_suffix(self.file_path.suffix + ".backup")
            shutil.copy2(self.file_path, backup_path)
        
        # Create temporary file
        fd, self.temp_path = tempfile.mkstemp(
            dir=self.file_path.parent,
            prefix=f".{self.file_path.stem}_",
            suffix=".tmp"
        )
        
        if "b" in self.mode:
            self.temp_file = os.fdopen(fd, self.mode)
        else:
            self.temp_file = os.fdopen(fd, self.mode, encoding=self.encoding)
        
        return self.temp_file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_file:
            self.temp_file.close()
        
        if exc_type is None:
            # Success - atomic rename
            if self.file_path.exists():
                shutil.copystat(self.file_path, self.temp_path)
            else:
                os.chmod(self.temp_path, 0o644)
            
            os.replace(self.temp_path, self.file_path)
            logger.debug(f"Atomic write completed: {self.file_path}")
        else:
            # Error - clean up temp file
            if self.temp_path and os.path.exists(self.temp_path):
                os.unlink(self.temp_path)
            logger.error(f"Atomic write failed: {self.file_path}: {exc_val}")
        
        return False