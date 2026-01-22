#!/usr/bin/env python3
"""Backup utility for MERIDIAN artifacts and state"""

import argparse
import json
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from meridian.logging_config import setup_logging, get_logger
from meridian.utils.exceptions import ErrorContext, FileOperationError

# Setup logging
logger = get_logger("meridian.backup")


class MeridianBackup:
    """Backup manager for MERIDIAN projects"""
    
    def __init__(self, project_path: Path, backup_dir: Optional[Path] = None):
        """
        Initialize backup manager.
        
        Args:
            project_path: Path to MERIDIAN project
            backup_dir: Directory for backups (default: ~/.meridian/backups)
        """
        self.project_path = Path(project_path).resolve()
        self.meridian_dir = self.project_path / ".meridian"
        
        if not self.meridian_dir.exists():
            raise FileOperationError(
                f"Not a MERIDIAN project: {project_path}",
                file_path=self.meridian_dir,
                operation_type="backup"
            )
        
        if backup_dir is None:
            self.backup_dir = Path.home() / ".meridian" / "backups"
        else:
            self.backup_dir = Path(backup_dir)
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(
        self,
        name: Optional[str] = None,
        include_data: bool = False,
        compress: bool = True
    ) -> Path:
        """
        Create backup of MERIDIAN project.
        
        Args:
            name: Backup name (default: timestamp)
            include_data: Include data/ directory
            compress: Compress backup with gzip
            
        Returns:
            Path to backup file
        """
        # Generate backup name
        if name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = self.project_path.name
            name = f"{project_name}_backup_{timestamp}"
        
        # Determine backup file extension
        ext = ".tar.gz" if compress else ".tar"
        backup_file = self.backup_dir / f"{name}{ext}"
        
        logger.info(f"Creating backup: {backup_file}")
        
        with ErrorContext("create_backup", backup_file=str(backup_file)):
            # Create tar archive
            mode = "w:gz" if compress else "w"
            with tarfile.open(backup_file, mode) as tar:
                # Always backup .meridian directory
                self._add_to_tar(tar, self.meridian_dir, ".meridian")
                
                # Backup configuration files
                config_files = [
                    "meridian.yaml",
                    "pyproject.toml",
                    "requirements.txt",
                    ".env"
                ]
                
                for config_file in config_files:
                    config_path = self.project_path / config_file
                    if config_path.exists():
                        self._add_to_tar(tar, config_path, config_file)
                
                # Backup PROJECT directory if exists
                project_dir = self.project_path / "PROJECT"
                if project_dir.exists():
                    self._add_to_tar(tar, project_dir, "PROJECT")
                
                # Optionally backup data
                if include_data:
                    data_dir = self.project_path / "data"
                    if data_dir.exists():
                        self._add_to_tar(tar, data_dir, "data")
            
            # Create metadata file
            metadata = {
                "backup_time": datetime.now().isoformat(),
                "project_path": str(self.project_path),
                "project_name": self.project_path.name,
                "backup_size": backup_file.stat().st_size,
                "included_data": include_data,
                "compressed": compress
            }
            
            metadata_file = backup_file.with_suffix(".json")
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(
                f"Backup created successfully: {backup_file} "
                f"({self._format_size(backup_file.stat().st_size)})"
            )
            
            return backup_file
    
    def restore_backup(
        self,
        backup_file: Path,
        target_path: Optional[Path] = None,
        overwrite: bool = False
    ) -> Path:
        """
        Restore backup to target directory.
        
        Args:
            backup_file: Path to backup file
            target_path: Where to restore (default: original location)
            overwrite: Overwrite existing files
            
        Returns:
            Path to restored project
        """
        backup_file = Path(backup_file)
        
        if not backup_file.exists():
            raise FileOperationError(
                f"Backup file not found",
                file_path=backup_file,
                operation_type="restore"
            )
        
        # Determine target path
        if target_path is None:
            # Try to read metadata
            metadata_file = backup_file.with_suffix(".json")
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                target_path = Path(metadata.get("project_path", self.project_path))
            else:
                target_path = self.project_path
        else:
            target_path = Path(target_path)
        
        logger.info(f"Restoring backup to: {target_path}")
        
        with ErrorContext("restore_backup", backup_file=str(backup_file), target=str(target_path)):
            # Check if target exists
            if target_path.exists() and not overwrite:
                raise FileOperationError(
                    f"Target directory exists and overwrite=False",
                    file_path=target_path,
                    operation_type="restore"
                )
            
            # Create target directory
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Extract backup
            mode = "r:gz" if backup_file.suffix == ".gz" else "r"
            with tarfile.open(backup_file, mode) as tar:
                tar.extractall(target_path)
            
            logger.info(f"Backup restored successfully to: {target_path}")
            return target_path
    
    def list_backups(self) -> List[dict]:
        """
        List available backups.
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        for backup_file in self.backup_dir.glob("*.tar*"):
            info = {
                "file": str(backup_file),
                "name": backup_file.stem,
                "size": self._format_size(backup_file.stat().st_size),
                "created": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
            }
            
            # Try to load metadata
            metadata_file = backup_file.with_suffix(".json")
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                    info.update(metadata)
                except:
                    pass
            
            backups.append(info)
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created"], reverse=True)
        
        return backups
    
    def cleanup_old_backups(self, keep_count: int = 5) -> List[Path]:
        """
        Remove old backups, keeping only the most recent ones.
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            List of deleted backup files
        """
        backups = self.list_backups()
        deleted = []
        
        if len(backups) <= keep_count:
            logger.info(f"No backups to clean up ({len(backups)} <= {keep_count})")
            return deleted
        
        # Delete old backups
        for backup_info in backups[keep_count:]:
            backup_file = Path(backup_info["file"])
            metadata_file = backup_file.with_suffix(".json")
            
            # Delete backup file
            if backup_file.exists():
                backup_file.unlink()
                deleted.append(backup_file)
                logger.info(f"Deleted old backup: {backup_file}")
            
            # Delete metadata
            if metadata_file.exists():
                metadata_file.unlink()
        
        return deleted
    
    def _add_to_tar(self, tar: tarfile.TarFile, source: Path, arcname: str):
        """Add file or directory to tar archive"""
        logger.debug(f"Adding to backup: {arcname}")
        tar.add(source, arcname=arcname)
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


def main():
    """CLI for backup utility"""
    parser = argparse.ArgumentParser(description="MERIDIAN Backup Utility")
    parser.add_argument(
        "action",
        choices=["create", "restore", "list", "cleanup"],
        help="Backup action to perform"
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Path to MERIDIAN project (default: current directory)"
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Directory for backups (default: ~/.meridian/backups)"
    )
    parser.add_argument(
        "--name",
        help="Backup name (for create action)"
    )
    parser.add_argument(
        "--include-data",
        action="store_true",
        help="Include data/ directory in backup"
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Don't compress backup"
    )
    parser.add_argument(
        "--backup-file",
        type=Path,
        help="Backup file to restore (for restore action)"
    )
    parser.add_argument(
        "--target",
        type=Path,
        help="Target directory for restore"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files during restore"
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Number of backups to keep (for cleanup action)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level)
    
    try:
        # Create backup manager
        backup_mgr = MeridianBackup(args.project, args.backup_dir)
        
        if args.action == "create":
            # Create backup
            backup_file = backup_mgr.create_backup(
                name=args.name,
                include_data=args.include_data,
                compress=not args.no_compress
            )
            print(f"Backup created: {backup_file}")
            
        elif args.action == "restore":
            # Restore backup
            if not args.backup_file:
                print("Error: --backup-file required for restore action")
                sys.exit(1)
            
            restored_path = backup_mgr.restore_backup(
                args.backup_file,
                target_path=args.target,
                overwrite=args.overwrite
            )
            print(f"Backup restored to: {restored_path}")
            
        elif args.action == "list":
            # List backups
            backups = backup_mgr.list_backups()
            
            if not backups:
                print("No backups found")
            else:
                print(f"Found {len(backups)} backup(s):\n")
                for backup in backups:
                    print(f"  {backup['name']}")
                    print(f"    File: {backup['file']}")
                    print(f"    Size: {backup['size']}")
                    print(f"    Created: {backup['created']}")
                    if backup.get('included_data'):
                        print(f"    Includes data: Yes")
                    print()
                    
        elif args.action == "cleanup":
            # Cleanup old backups
            deleted = backup_mgr.cleanup_old_backups(keep_count=args.keep)
            
            if deleted:
                print(f"Deleted {len(deleted)} old backup(s):")
                for file in deleted:
                    print(f"  - {file}")
            else:
                print("No backups to clean up")
                
    except Exception as e:
        logger.error(f"Backup operation failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()